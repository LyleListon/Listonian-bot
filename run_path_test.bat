@echo off
setlocal

echo ===========================================================
echo Path Finder Test Runner
echo ===========================================================
echo.

echo Current directory: %~dp0
cd /d %~dp0

echo.
echo Step 1: Activating virtual environment...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Virtual environment activated
) else (
    echo WARNING: Virtual environment not found at venv\Scripts\activate.bat
    echo Attempting to use system Python
)

echo.
echo Step 2: Running path finder test with 10 test cases...
echo This will save results to data\tests directory
echo.

echo Running test...
python test_path_finder.py --max-tests 10 --output-dir data\tests > test_results.txt 2>&1

echo.
echo Step 3: Test completed. Results saved to test_results.txt

echo.
echo Displaying test results:
echo -----------------------------------------------------------
type test_results.txt
echo -----------------------------------------------------------
echo.

echo Test completed. The full results have been saved to:
echo %~dp0test_results.txt
echo.

echo If you'd like to view detailed results, check the data\tests directory
echo where JSON and CSV files with all test data have been saved.
echo.

echo Press any key to exit...
pause > nul