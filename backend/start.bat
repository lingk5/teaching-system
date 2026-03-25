@echo off
cd /d %~dp0

if not exist venv (
    echo [INFO] Virtual environment not found. Creating one...
    python fix_env.py
)

call venv\Scripts\activate.bat
echo [INFO] Starting server...
python run.py
pause