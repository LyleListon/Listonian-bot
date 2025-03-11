@echo off
echo Cleaning up test artifacts before production deployment...
echo.

REM Remove test configuration files
echo Removing test configuration files...
if exist "configs\test_config.json" del /f /q "configs\test_config.json"
if exist "configs\example_production_config.json" del /f /q "configs\example_production_config.json"
if exist "configs\local.json" del /f /q "configs\local.json"
if exist "configs\default.json" del /f /q "configs\default.json"

REM Remove test reports
echo Removing test reports...
if exist "test_reports" rmdir /s /q "test_reports"

REM Clean up mock data
echo Cleaning up mock data...
if exist "data\test_results" rmdir /s /q "data\test_results"
if exist "data\mock_data" rmdir /s /q "data\mock_data"

REM Clean up test logs
echo Cleaning up test logs...
if exist "logs\test_*.log" del /f /q "logs\test_*.log"
if exist "logs\test_runner.log" del /f /q "logs\test_runner.log"

echo.
echo Test artifacts cleanup complete!
echo Please proceed with production deployment.
echo.
pause