@echo off
echo ===============================================================================
echo ARBITRAGE SYSTEM DASHBOARD (NEW)
echo ===============================================================================
echo.
echo Starting new dashboard...

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if FastAPI and Uvicorn are installed
echo Checking required packages...
set MISSING_PACKAGES=0

pip show fastapi >nul 2>&1 || set MISSING_PACKAGES=1
pip show uvicorn >nul 2>&1 || set MISSING_PACKAGES=1
pip show python-dotenv >nul 2>&1 || set MISSING_PACKAGES=1

if %MISSING_PACKAGES% neq 0 (
    echo Installing required packages...
    pip install -r new_dashboard/dashboard_requirements.txt
)

REM Check for .env file
if not exist "%~dp0.env" (
    echo No .env file found. Creating from example...
    if exist "%~dp0.env.example" (
        copy "%~dp0.env.example" "%~dp0.env"
        echo.
        echo Created .env file. You need to edit it with your RPC URL!
        echo Please open %~dp0.env and set BASE_RPC_URL to your Base network RPC URL
        echo.
        
        set /p EDIT_NOW="Would you like to edit the .env file now? (y/n): "
        if /i "%EDIT_NOW%"=="y" (
            REM Try to open with various editors
            where code >nul 2>&1 && (code "%~dp0.env" & goto :EDITOR_FOUND)
            where notepad++ >nul 2>&1 && (notepad++ "%~dp0.env" & goto :EDITOR_FOUND)
            notepad "%~dp0.env"
            :EDITOR_FOUND
        ) else (
            echo Please remember to edit the .env file before using the dashboard.
        )
    ) else (
        echo ERROR: .env.example not found! Please create a .env file manually.
        echo The file should contain at minimum: BASE_RPC_URL=your_rpc_url_here
    )
)

REM Create required directories
mkdir new_dashboard\static 2>nul
mkdir new_dashboard\static\css 2>nul
mkdir new_dashboard\static\js 2>nul
mkdir new_dashboard\templates 2>nul

REM Start the dashboard
echo Starting dashboard server...
cd new_dashboard
python app.py --host localhost --port 8080
cd ..

echo.
echo ===============================================================================
echo Press any key to exit...
pause >nul