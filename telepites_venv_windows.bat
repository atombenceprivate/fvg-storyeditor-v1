@echo off
REM Virtuális környezet és függőségek telepítése Windows alatt.
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Hiba: Python 3 nem talalhato. Telepitsd a python.org oldalrol.
    pause
    exit /b 1
)

py -3 -m venv .venv
if errorlevel 1 goto :hiba
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :hiba
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :hiba

echo.
echo Kesz. Inditas: FVG Story Editor.bat
pause
exit /b 0

:hiba
echo.
echo A telepites nem sikerult.
pause
exit /b 1
