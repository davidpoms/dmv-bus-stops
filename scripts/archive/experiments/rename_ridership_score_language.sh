#!/bin/bash

set -e

python - <<'PY'
from pathlib import Path

files = [
    Path("src/scoring/calculate_stop_priority.py"),
    Path("src/assessment/create_opportunity_assessments.py"),
    Path("src/assessment/score_improvement_opportunities.py"),
]

for path in files:
    text = path.read_text()

    text = text.replace(
        '"ridership": {',
        '"route_exposure": {'
    )

    text = text.replace(
        '"ridership_score"',
        '"route_exposure_score"'
    )

    path.write_text(text)

    print(f"Updated {path}")

PY

python -m py_compile \
src/scoring/calculate_stop_priority.py \
src/assessment/create_opportunity_assessments.py \
src/assessment/score_improvement_opportunities.py

echo "Syntax checks passed."
