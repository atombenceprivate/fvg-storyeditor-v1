#!/usr/bin/env bash
# A Forgatókönyvíró indítójának telepítése a jelenlegi felhasználó
# Alkalmazások menüjébe. Nem igényel rendszergazdai jogosultságot.
set -euo pipefail

script_mappa="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cel_mappa="$HOME/.local/share/applications"
mkdir -p "$cel_mappa"
cp "$script_mappa/Forgatokonyviro.desktop" "$cel_mappa/forgatokonyviro.desktop"
chmod +x "$cel_mappa/forgatokonyviro.desktop"

if command -v xdg-mime >/dev/null 2>&1; then
    xdg-mime install --mode user "$script_mappa/fvgscript-mime.xml"
    xdg-mime default forgatokonyviro.desktop application/x-fvgscript
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$cel_mappa"
fi

echo "Kész. Keresd meg az Alkalmazások között: FVG Story Editor"
