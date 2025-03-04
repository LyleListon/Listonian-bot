@echo off
echo Running Flash Loan Integration Tests...
echo.

python -m tests.finance.test_flash_loans

echo.
echo Flash Loan Tests completed.
pause