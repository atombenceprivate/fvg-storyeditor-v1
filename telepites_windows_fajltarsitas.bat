@echo off
REM A .fvgscript fájlok társítása az FVG Story Editorhoz csak az aktuális Windows-felhasználónál.
REM Nem igényel rendszergazdai jogosultságot.
setlocal
set "APP_DIR=%~dp0"

reg add "HKCU\Software\Classes\.fvgscript" /ve /t REG_SZ /d "FVGStoryEditor.Script" /f >nul
reg add "HKCU\Software\Classes\FVGStoryEditor.Script" /ve /t REG_SZ /d "FVG Story Editor projekt" /f >nul
reg add "HKCU\Software\Classes\FVGStoryEditor.Script\shell\open\command" /ve /t REG_SZ /d "\"%APP_DIR%FVG Story Editor.bat\" \"%%1\"" /f >nul

if errorlevel 1 (
    echo A fajltarsitas nem sikerult.
    pause
    exit /b 1
)

echo.
echo Kesz. A .fvgscript fajlok mostantol az FVG Story Editorral nyilnak meg.
echo Ha az ikon nem frissul azonnal, inditsd ujra a Fajlkezelot vagy a Windowst.
pause
