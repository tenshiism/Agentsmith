@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "VENV_DIR=%ROOT_DIR%\.venv"

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [INFO] No .venv found at %VENV_DIR%
    choice /C YN /M "Create a new virtual environment here"
    if errorlevel 2 exit /b 1
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        exit /b 1
    )
    echo [OK] Virtual environment created
)
call "%VENV_DIR%\Scripts\activate.bat"
echo [INFO] Installing requirements...
pip install -r "%ROOT_DIR%\requirements.txt"
