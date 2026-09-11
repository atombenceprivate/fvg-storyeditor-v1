; FVG Story Editor - Windows NSIS telepítő
; Fordítás: makensis installer\fvg-story-editor.nsi

Unicode True
!include "MUI2.nsh"
!include "LogicLib.nsh"

!define APP_NAME "FVG Story Editor"
!define APP_VERSION "0.2.0"
!define APP_PUBLISHER "FVG Story Editor"
!define APP_EXE "FVG Story Editor.bat"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "..\dist\FVG-Story-Editor-Setup-${APP_VERSION}.exe"
InstallDir "$LOCALAPPDATA\FVG Story Editor"
RequestExecutionLevel user
BrandingText "FVG Story Editor"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Hungarian"

Function .onInit
  ; A Python Launcher a hivatalos Windows Python telepítés része.
  nsExec::ExecToStack 'py -3 --version'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONSTOP|MB_OK "A Python 3 nem található. Telepítsd a Python 3-at a python.org oldalról (a Python Launcherrel együtt), majd futtasd újra a telepítőt."
    Abort
  ${EndIf}
FunctionEnd

Section "FVG Story Editor" SEC_MAIN
  SetOutPath "$INSTDIR"
  File "..\app.py"
  File "..\requirements.txt"
  File "..\FVG Story Editor.bat"
  File "..\telepites_venv_windows.bat"
  File "..\telepites_windows_fajltarsitas.bat"
  File "..\eltavolitas_windows_fajltarsitas.bat"
  File "..\LICENSE"
  File "..\CHANGELOG.md"

  ; A saját virtuális környezet telepítése biztosítja a PDF-export függőségét.
  DetailPrint "Virtuális környezet és függőségek telepítése..."
  nsExec::ExecToLog 'py -3 -m venv "$INSTDIR\.venv"'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONEXCLAMATION|MB_OK "A virtuális környezet nem készült el. Az alkalmazás elindulhat, de a PDF-exporthoz futtasd később a telepites_venv_windows.bat fájlt."
  ${Else}
    nsExec::ExecToLog '"$INSTDIR\.venv\Scripts\python.exe" -m pip install -r "$INSTDIR\requirements.txt"'
    Pop $0
    ${If} $0 != 0
      MessageBox MB_ICONEXCLAMATION|MB_OK "A PDF-export függőségei nem települtek. Az alkalmazás ettől még használható; a telepites_venv_windows.bat később újraindítható."
    ${EndIf}
  ${EndIf}

  CreateDirectory "$SMPROGRAMS\FVG Story Editor"
  CreateShortCut "$SMPROGRAMS\FVG Story Editor\FVG Story Editor.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortCut "$DESKTOP\FVG Story Editor.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

  ; Felhasználói szintű .fvgscript társítás.
  WriteRegStr HKCU "Software\Classes\.fvgscript" "" "FVGStoryEditor.Script"
  WriteRegStr HKCU "Software\Classes\FVGStoryEditor.Script" "" "FVG Story Editor projekt"
  WriteRegStr HKCU "Software\Classes\FVGStoryEditor.Script\shell\open\command" "" '"$INSTDIR\FVG Story Editor.bat" "%1"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FVGStoryEditor" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FVGStoryEditor" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FVGStoryEditor" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\FVG Story Editor\FVG Story Editor.lnk"
  RMDir "$SMPROGRAMS\FVG Story Editor"
  Delete "$DESKTOP\FVG Story Editor.lnk"
  DeleteRegKey HKCU "Software\Classes\.fvgscript"
  DeleteRegKey HKCU "Software\Classes\FVGStoryEditor.Script"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FVGStoryEditor"
  RMDir /r "$INSTDIR"
SectionEnd
