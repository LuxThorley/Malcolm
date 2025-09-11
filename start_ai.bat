@echo off
setlocal

:: === CONFIG ===
set VENV_DIR=malcolmai_env
set REQ_FILE=requirements.txt
set GIT_MSG=Auto-commit and deploy by start_ai.bat
set FLY_APP=malcolmai-api

echo ===========================================
echo 🚀 Malcolm AI Auto Launcher
echo ===========================================

:: === Activate virtual environment ===
if not exist %VENV_DIR% (
    echo [INFO] Creating virtual environment...
    python -m venv %VENV_DIR%
)
call %VENV_DIR%\Scripts\activate

:: === Upgrade pip inside venv ===
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

:: === Install requirements ===
echo [INFO] Installing requirements...
pip install -r %REQ_FILE%

:: === Git commit and push ===
echo [INFO] Committing and pushing to GitHub...
git add .
git commit -m "%GIT_MSG%"
git push origin main

:: === Deploy to Fly.io ===
echo [INFO] Deploying to Fly.io...
fly deploy --app %FLY_APP%

:: === Run the API locally ===
echo [INFO] Starting API locally...
python malcolmai_api.py

pause
