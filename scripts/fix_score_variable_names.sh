#!/bin/bash

set -e

FILE="src/assessment/score_improvement_opportunities.py"

python - <<'PY'
from pathlib import Path

path = Path("src/assessment/score_improvement_opportunities.py")

text = path.read_text()

text = text.replace(
    "ridership_score,",
    "route_exposure_score,"
)

text = text.replace(
    "route_score,",
    "connectivity_score,"
)

text = text.replace(
    "complexity_score,",
    "physical_complexity_score,"
)

path.write_text(text)

print("Fixed remaining score variable references.")
PY

python -m py_compile "$FILE"

echo "Syntax check passed."
