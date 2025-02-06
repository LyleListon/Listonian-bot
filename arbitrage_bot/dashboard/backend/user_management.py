"""User management system for the dashboard."""

from fastapi import FastAPI, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from .auth import auth_manager, AuthManager

class UserRole(BaseModel):
    """User role definition."""
    name: str
    permissions: List[str]
    description: str

class UserProfile(BaseModel):
    """Extended user profile information."""
    id: str
    email: str
    name: Optional[str]
    picture: Optional[str]
    provider: str
    role: str
    created_at: datetime
    last_login: datetime
    is_active: bool
    settings: Dict[str, Any]

class UserUpdate(BaseModel):
    """User update request model."""
    name: Optional[str]
    role: Optional[str]
    is_active: Optional[bool]
    settings: Optional[Dict[str, Any]]

# Default roles and permissions
DEFAULT_ROLES = {
    "admin": UserRole(
        name="admin",
        permissions=[
            "manage_users",
            "manage_roles",
            "view_all_data",
            "manage_system",
        ],
        description="Full system access"
    ),
    "manager": UserRole(
        name="manager",
        permissions=[
            "view_all_data",
            "manage_trading",
            "view_analytics",
        ],
        description="Trading and analytics management"
    ),
    "viewer": UserRole(
        name="viewer",
        permissions=[
            "view_basic_data",
            "view_own_profile",
        ],
        description="Basic view access"
    )
}

class UserManager:
    """Manage user profiles, roles, and permissions."""
    
    def __init__(self, auth_manager: AuthManager):
        """Initialize user manager."""
        self.auth_manager = auth_manager
        self.roles = DEFAULT_ROLES.copy()
        self.user_profiles: Dict[str, UserProfile] = {}
        
    async def get_user_profile(self, user_id: str) -> UserProfile:
        """Get user profile by ID."""
        if user_id not in self.user_profiles:
            # Create profile if it doesn't exist
            user = self.auth_manager.active_sessions.get(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
                
            self.user_profiles[user_id] = UserProfile(
                id=user_id,
                email=user["email"],
                name=user.get("name"),
                picture=user.get("picture"),
                provider=user["provider"],
                role="viewer",  # Default role
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow(),
                is_active=True,
                settings={}
            )
            
        return self.user_profiles[user_id]
        
    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[str] = None
    ) -> List[UserProfile]:
        """List user profiles with optional filtering."""
        users = list(self.user_profiles.values())
        
        if role:
            users = [u for u in users if u.role == role]
            
        return users[skip:skip + limit]
        
    async def update_user(
        self,
        user_id: str,
        update_data: UserUpdate,
        current_user: Dict[str, Any]
    ) -> UserProfile:
        """Update user profile."""
        # Check permissions
        current_profile = await self.get_user_profile(current_user["id"])
        if current_profile.role != "admin" and current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update other users"
            )
            
        profile = await self.get_user_profile(user_id)
        
        # Update fields
        if update_data.name is not None:
            profile.name = update_data.name
            
        if update_data.role is not None:
            if current_profile.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can change roles"
                )
            if update_data.role not in self.roles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role: {update_data.role}"
                )
            profile.role = update_data.role
            
        if update_data.is_active is not None:
            if current_profile.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can change active status"
                )
            profile.is_active = update_data.is_active
            
        if update_data.settings is not None:
            profile.settings.update(update_data.settings)
            
        return profile
        
    async def get_role(self, role_name: str) -> UserRole:
        """Get role by name."""
        if role_name not in self.roles:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role not found: {role_name}"
            )
        return self.roles[role_name]
        
    async def list_roles(self) -> List[UserRole]:
        """List all roles."""
        return list(self.roles.values())

# Create user manager instance
user_manager = UserManager(auth_manager)

async def init_user_routes(app: FastAPI):
    """Initialize user management routes."""
    
    @app.get('/api/users/me', response_model=UserProfile)
    async def get_current_user_profile(
        current_user: Dict[str, Any] = Depends(auth_manager.get_current_user)
    ):
        """Get current user's profile."""
        return await user_manager.get_user_profile(current_user["id"])
        
    @app.get('/api/users', response_model=List[UserProfile])
    async def list_users(
        skip: int = 0,
        limit: int = 100,
        role: Optional[str] = None,
        current_user: Dict[str, Any] = Depends(auth_manager.get_current_user)
    ):
        """List users with optional filtering."""
        # Check permissions
        current_profile = await user_manager.get_user_profile(current_user["id"])
        if current_profile.role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to list users"
            )
            
        return await user_manager.list_users(skip, limit, role)
        
    @app.get('/api/users/{user_id}', response_model=UserProfile)
    async def get_user_profile(
        user_id: str,
        current_user: Dict[str, Any] = Depends(auth_manager.get_current_user)
    ):
        """Get user profile by ID."""
        # Check permissions
        current_profile = await user_manager.get_user_profile(current_user["id"])
        if current_profile.role not in ["admin", "manager"] and current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this profile"
            )
            
        return await user_manager.get_user_profile(user_id)
        
    @app.patch('/api/users/{user_id}', response_model=UserProfile)
    async def update_user_profile(
        user_id: str,
        update_data: UserUpdate,
        current_user: Dict[str, Any] = Depends(auth_manager.get_current_user)
    ):
        """Update user profile."""
        return await user_manager.update_user(user_id, update_data, current_user)
        
    @app.get('/api/roles', response_model=List[UserRole])
    async def list_roles(
        current_user: Dict[str, Any] = Depends(auth_manager.get_current_user)
    ):
        """List all roles."""
        current_profile = await user_manager.get_user_profile(current_user["id"])
        if current_profile.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to list roles"
            )
            
        return await user_manager.list_roles()
        
    @app.get('/api/roles/{role_name}', response_model=UserRole)
    async def get_role(
        role_name: str,
        current_user: Dict[str, Any] = Depends(auth_manager.get_current_user)
    ):
        """Get role by name."""
        current_profile = await user_manager.get_user_profile(current_user["id"])
        if current_profile.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view roles"
            )
            
        return await user_manager.get_role(role_name)