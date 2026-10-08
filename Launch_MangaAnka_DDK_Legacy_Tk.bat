@echo off
setlocal
cd /d "%~dp0"
echo MangaAnka DDK - Legacy / Recovery Tk Frontend
if exist ".venv-qt\Scripts\python.exe" (
  ".venv-qt\Scripts\python.exe" mangaanka_database_development_kit.py %*
  exit /b
)
py mangaanka_database_development_kit.py %*
