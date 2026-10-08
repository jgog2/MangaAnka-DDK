@echo off
cd /d "%~dp0"
if not exist ".venv-qt\Scripts\python.exe" (
    echo Create the local Qt environment first:
    echo python -m venv .venv-qt
    echo .venv-qt\Scripts\python.exe -m pip install -r requirements-qt.txt
    pause
    exit /b 1
)
".venv-qt\Scripts\python.exe" mangaanka_qt.py %*
