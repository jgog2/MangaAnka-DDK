@echo off
setlocal
cd /d "%~dp0"
echo MangaAnka DDK - Primary Qt EXE Builder
if not exist ".venv-qt\Scripts\python.exe" goto dependencies
".venv-qt\Scripts\python.exe" -c "import PySide6, PyInstaller" >nul 2>nul
if errorlevel 1 goto dependencies
".venv-qt\Scripts\python.exe" -m PyInstaller --noconfirm MangaAnka-Database-Development-Kit.spec
if errorlevel 1 (
  echo BUILD FAILED.
  pause
  exit /b 1
)
echo Build complete: %CD%\dist\MangaAnka-Database-Development-Kit.exe
pause
exit /b 0
:dependencies
echo Create the local build environment, then rerun:
echo python -m venv .venv-qt
echo .venv-qt\Scripts\python.exe -m pip install -r requirements-build.txt
pause
exit /b 1
