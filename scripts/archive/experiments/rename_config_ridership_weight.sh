#!/bin/bash

set -e

python - <<'PY'
from pathlib import Path

path = Path("src/config.py")

text = path.read_text()

text = text.replace(
    '"ridership":',
    '"route_exposure":'
)

path.write_text(text)

print("Updated config scoring label.")
PY

python -m py_compile src/config.py

echo "Syntax check passed."
