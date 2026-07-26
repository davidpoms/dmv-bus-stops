#!/bin/bash

set -e

python - <<'PY'
from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

start = text.find("def get_stop_evidence_summary(stop_id):")

if start == -1:
    raise SystemExit("Helper not found")

# capture until end of function block
end = text.find("\n\n", start)

# keep searching until we find the next top-level definition/decorator
lines = text[start:].splitlines(True)

block = []
for line in lines:
    if block and (line.startswith("def ") or line.startswith("@app.route")):
        break
    block.append(line)

helper = "".join(block).rstrip() + "\n\n"

# remove original helper
text = text.replace(helper, "", 1)

# insert before first Flask route
marker = "@app.route"

idx = text.find(marker)

if idx == -1:
    raise SystemExit("No route marker found")

text = text[:idx] + helper + text[idx:]

path.write_text(text)

print("Moved get_stop_evidence_summary helper.")

PY

python -m py_compile src/api/app.py

echo "Syntax check passed."
