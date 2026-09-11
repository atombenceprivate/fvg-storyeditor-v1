@echo off
REM A felhasználói .fvgscript társítás eltávolítása.
reg delete "HKCU\Software\Classes\.fvgscript" /f >nul 2>&1
reg delete "HKCU\Software\Classes\FVGStoryEditor.Script" /f >nul 2>&1
echo Az FVG Story Editor fajltarsitasa el lett tavolitva.
pause
