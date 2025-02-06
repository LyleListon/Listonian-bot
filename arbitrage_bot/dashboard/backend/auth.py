"""Authentication system using OAuth2 with Google and GitHub providers."""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.middleware.cors import CORSMiddleware
from starlette.config import Config
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

# Load configuration
config = Config(".env")
SECRET_KEY = config("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configure OAuth providers
oauth = OAuth()
oauth.register(
    name='google',
    client_id=config("GOOGLE_CLIENT_ID"),
    client_secret=config("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

oauth.register(
    name='github',
    client_id=config("GITHUB_CLIENT_ID"),
    client_secret=config("GITHUB_CLIENT_SECRET"),
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthManager:
    """Manage authentication and user sessions."""
    
    def __init__(self):
        """Initialize auth manager."""
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
            
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
        
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    async def get_current_user(
        self,
        request: Request,
        token: str = Depends(OAuth2AuthorizationCodeBearer(
            authorizationUrl="",
            tokenUrl="",
        ))
    ) -> Dict[str, Any]:
        """Get current authenticated user."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = await self.verify_token(token)
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
                
            if user_id not in self.active_sessions:
                raise credentials_exception
                
            return self.active_sessions[user_id]
            
        except jwt.PyJWTError:
            raise credentials_exception

# Create auth manager instance
auth_manager = AuthManager()

async def init_oauth_routes(app: FastAPI):
    """Initialize OAuth routes."""
    
    @app.get('/auth/login/{provider}')
    async def login(provider: str, request: Request):
        """Start OAuth login flow."""
        if provider not in ['google', 'github']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider: {provider}"
            )
            
        try:
            redirect_uri = request.url_for(f'auth_{provider}_callback')
            return await oauth.create_client(provider).authorize_redirect(
                request, redirect_uri
            )
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Authentication failed"
            )
            
    @app.get('/auth/google/callback')
    async def auth_google_callback(request: Request):
        """Handle Google OAuth callback."""
        try:
            token = await oauth.google.authorize_access_token(request)
            user = await oauth.google.parse_id_token(request, token)
            
            # Create session
            access_token = await auth_manager.create_access_token(
                data={"sub": user["sub"], "email": user["email"]},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            # Store user info
            auth_manager.active_sessions[user["sub"]] = {
                "id": user["sub"],
                "email": user["email"],
                "name": user.get("name"),
                "picture": user.get("picture"),
                "provider": "google"
            }
            
            return JSONResponse({
                "access_token": access_token,
                "token_type": "bearer"
            })
            
        except OAuthError as e:
            logger.error(f"Google OAuth error: {e}")
            raise HTTPException(
                status_code=400,
                detail="Failed to authenticate with Google"
            )
            
    @app.get('/auth/github/callback')
    async def auth_github_callback(request: Request):
        """Handle GitHub OAuth callback."""
        try:
            token = await oauth.github.authorize_access_token(request)
            resp = await oauth.github.get('user', token=token)
            user = resp.json()
            
            # Get email
            emails = await oauth.github.get('user/emails', token=token)
            primary_email = next(
                (email for email in emails.json() if email["primary"]),
                None
            )
            
            if not primary_email:
                raise HTTPException(
                    status_code=400,
                    detail="No primary email found"
                )
                
            # Create session
            access_token = await auth_manager.create_access_token(
                data={"sub": str(user["id"]), "email": primary_email["email"]},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            # Store user info
            auth_manager.active_sessions[str(user["id"])] = {
                "id": str(user["id"]),
                "email": primary_email["email"],
                "name": user.get("name"),
                "picture": user.get("avatar_url"),
                "provider": "github"
            }
            
            return JSONResponse({
                "access_token": access_token,
                "token_type": "bearer"
            })
            
        except OAuthError as e:
            logger.error(f"GitHub OAuth error: {e}")
            raise HTTPException(
                status_code=400,
                detail="Failed to authenticate with GitHub"
            )
            
    @app.get('/auth/user')
    async def get_user(user: Dict[str, Any] = Depends(auth_manager.get_current_user)):
        """Get current user info."""
        return user
        
    @app.post('/auth/logout')
    async def logout(user: Dict[str, Any] = Depends(auth_manager.get_current_user)):
        """Logout user."""
        if user["id"] in auth_manager.active_sessions:
            del auth_manager.active_sessions[user["id"]]
        return {"message": "Successfully logged out"}