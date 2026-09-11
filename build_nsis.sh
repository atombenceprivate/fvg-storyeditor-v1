#!/usr/bin/env bash
# NSIS Windows telepítő építése Linuxról vagy Windowsról, ha a makensis elérhető.
set -euo pipefail

projekt_mappa="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v makensis >/dev/null 2>&1; then
    echo "A makensis nem található. Ubuntu/Debian: sudo apt install nsis"
    exit 1
fi

mkdir -p "$projekt_mappa/dist"
cd "$projekt_mappa/installer"
makensis fvg-story-editor.nsi
