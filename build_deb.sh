#!/usr/bin/env bash
# Az FVG Story Editor telepíthető Debian/Ubuntu csomagjának elkészítése.
set -euo pipefail

projekt_mappa="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
csomag_mappa="$(mktemp -d)"
trap 'rm -rf "$csomag_mappa"' EXIT

install -d "$csomag_mappa/DEBIAN" "$csomag_mappa/opt/fvg-story-editor" "$csomag_mappa/usr/bin" "$csomag_mappa/usr/share/applications" "$csomag_mappa/usr/share/mime/packages"
install -m 644 "$projekt_mappa/packaging/debian/DEBIAN/control" "$csomag_mappa/DEBIAN/control"
install -m 755 "$projekt_mappa/packaging/debian/DEBIAN/postinst" "$csomag_mappa/DEBIAN/postinst"
install -m 755 "$projekt_mappa/packaging/debian/usr/bin/fvg-story-editor" "$csomag_mappa/usr/bin/fvg-story-editor"
install -m 644 "$projekt_mappa/packaging/debian/usr/share/applications/fvg-story-editor.desktop" "$csomag_mappa/usr/share/applications/fvg-story-editor.desktop"
install -m 644 "$projekt_mappa/fvgscript-mime.xml" "$csomag_mappa/usr/share/mime/packages/fvgscript-mime.xml"
install -m 644 "$projekt_mappa/app.py" "$csomag_mappa/opt/fvg-story-editor/app.py"
install -m 644 "$projekt_mappa/requirements.txt" "$csomag_mappa/opt/fvg-story-editor/requirements.txt"

install -d "$projekt_mappa/dist"
dpkg-deb --build --root-owner-group "$csomag_mappa" "$projekt_mappa/dist/fvg-story-editor_0.1.0_all.deb"
echo "Elkészült: $projekt_mappa/dist/fvg-story-editor_0.1.0_all.deb"
