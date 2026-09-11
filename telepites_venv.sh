#!/usr/bin/env bash
# Virtuális környezet és a PDF-export függőségeinek telepítése Linux/macOS alatt.
set -euo pipefail

script_mappa="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python_parancs="${PYTHON_BIN:-python3}"

if ! command -v "$python_parancs" >/dev/null 2>&1; then
    echo "Hiba: Python 3 nem található. Telepítsd a python3 csomagot."
    exit 1
fi

cd "$script_mappa"
if ! "$python_parancs" -m ensurepip --version >/dev/null 2>&1; then
    echo "Hiba: ebből a Pythonból hiányzik az ensurepip/venv támogatás."
    echo "Ubuntu/Debian alatt futtasd egyszer terminálban:"
    echo "  sudo apt install python3.14-venv"
    echo "Ezután indítsd újra ezt a telepítőt."
    exit 1
fi
"$python_parancs" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
echo "Kész. Indítás: ./inditas.sh"
