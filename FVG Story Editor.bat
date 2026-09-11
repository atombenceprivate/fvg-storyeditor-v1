@echo off
REM Windows-indító az FVG Story Editorhoz.
REM A fájl mappájából indul, ezért áthelyezés után is működik.
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Python 3 nem talalhato. Telepitsd a Python 3-at a python.org oldalrol.
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe app.py "%~1"
    goto :vege
)

py -3 app.py "%~1"

:vege
if errorlevel 1 (
    echo.
    echo Az FVG Story Editor indítása nem sikerült.
    echo Ellenőrizd, hogy a Python 3 és a Tkinter telepítve van-e.
    pause
)
