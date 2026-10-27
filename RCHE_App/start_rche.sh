#!/usr/bin/env bash
cd "$(dirname "$0")"
if [ ! -x venv/bin/python ]; then
  python3 -m venv venv && venv/bin/python -m pip install --upgrade pip && venv/bin/python -m pip install -r requirements.txt || exit 1
fi
RCHE_OPEN_BROWSER=1 venv/bin/python app.py
