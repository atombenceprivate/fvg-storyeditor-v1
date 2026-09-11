#!/usr/bin/env bash
# Az .desktop fájl innen indítja a programot. A kimenetet naplózzuk, mert
# egy grafikus indításnál egyébként az indulási hiba láthatatlan maradna.
script_mappa="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
naplo="$script_mappa/inditasi_hiba.log"

printf '%s – Indítás megkísérelve.\n' "$(date --iso-8601=seconds)" >> "$naplo"
cd "$script_mappa" || exit 1
if [[ -x "$script_mappa/.venv/bin/python" ]]; then
    exec "$script_mappa/.venv/bin/python" "$script_mappa/app.py" "$@" >> "$naplo" 2>&1
fi
exec /usr/bin/python3 "$script_mappa/app.py" "$@" >> "$naplo" 2>&1
