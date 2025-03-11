@echo off
echo Cleaning up diagnostic files...

set files_to_delete=^
check_python.py ^
check_python_installation.bat ^
run_diagnostic.bat ^
rebuild_venv.bat ^
fixed_rebuild_venv.bat ^
memory_efficient_rebuild.bat ^
fix_vscode_python.bat

for %%f in (%files_to_delete%) do (
    if exist "%%f" (
        echo Deleting %%f...
        del "%%f"
    ) else (
        echo %%f not found, skipping...
    )
)

echo.
echo Cleanup complete!
echo.
pause