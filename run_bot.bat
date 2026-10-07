@echo off
echo =========================================
echo       US Visa Automation Bot           
echo =========================================

echo Checking Python installation...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ and check "Add to PATH" during installation.
    pause
    exit /b
)

echo Setting up Virtual Environment...
IF NOT EXIST "venv" (
    python -m venv venv
)

echo Installing Dependencies (this might take a minute)...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\pip.exe install -r requirements.txt

echo Starting the Web Dashboard...
start http://127.0.0.1:5000
venv\Scripts\python.exe app.py
pause
