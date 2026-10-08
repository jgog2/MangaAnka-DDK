@echo off
setlocal
cd /d "%~dp0"
if exist "dist\MangaAnka-Database-Development-Kit.exe" (
  start "" "dist\MangaAnka-Database-Development-Kit.exe" %*
  exit /b 0
)
call "%~dp0Launch_MangaAnka_DDK_Qt.bat" %*
