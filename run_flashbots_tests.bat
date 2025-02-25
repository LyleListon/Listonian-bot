@echo off
echo Running Flash Loan and Flashbots Integration Tests
echo =================================================

REM Create a Python virtual environment if it doesn't exist
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements-dev.txt
) else (
    call venv\Scripts\activate
)

REM Install the package in development mode if needed
pip install -e .

echo.
echo Running unit tests...
echo -------------------
python -m pytest tests/unit/test_flash_loan_flashbots_unit.py -v

echo.
echo Running integration tests...
echo --------------------------
python -m pytest tests/integration/test_flash_loan_flashbots.py -v -xvs

echo.
echo Tests complete!
echo ==============

REM Keep terminal open if there were errors
if %ERRORLEVEL% neq 0 (
    echo.
    echo Tests failed with error code: %ERRORLEVEL%
    pause
) else (
    echo All tests passed successfully!
)