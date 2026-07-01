@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "VENV_DIR=%ROOT_DIR%\.venv"

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [ERROR] No virtual environment found. Run venv_start.bat first.
    exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"

if "%~1"=="" (
    set "CONFIG=%ROOT_DIR%\configs\default.json"
) else (
    set "CONFIG=%~1"
)

python "%ROOT_DIR%\main.py" --config "%CONFIG%" %2 %3 %4 %5 %6 %7 %8 %9
