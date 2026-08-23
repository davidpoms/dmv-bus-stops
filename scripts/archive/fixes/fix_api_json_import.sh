#!/bin/bash

set -e

FILE="src/api/app.py"

python - <<'PY'
from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

if "import json" not in text:
    text = "import json\n\n" + text
    path.write_text(text)
    print("Added json import.")
else:
    print("json import already exists.")

PY

python -m py_compile src/api/app.py

echo "Syntax check passed."
