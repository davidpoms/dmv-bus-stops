#!/bin/bash

set -e

echo "Updating create_opportunity_assessments.py..."

python - <<'PY'
from pathlib import Path

files = [
    Path("src/assessment/create_opportunity_assessments.py"),
    Path("src/assessment/score_improvement_opportunities.py"),
    Path("src/assessment/generate_impact_summary.py"),
    Path("src/scoring/calculate_stop_priority.py"),
]

for path in files:
    if not path.exists():
        continue

    text = path.read_text()

    text = text.replace(
        "average_daily_weekday_boardings",
        "combined_route_weekday_boardings"
    )

    text = text.replace(
        "highest_route_daily_boardings",
        "highest_route_weekday_boardings"
    )

    text = text.replace(
        "total_daily_weekday_boardings",
        "combined_route_weekday_boardings"
    )

    path.write_text(text)

    print(f"Updated {path}")

PY

python -m py_compile \
src/assessment/create_opportunity_assessments.py \
src/assessment/score_improvement_opportunities.py \
src/assessment/generate_impact_summary.py \
src/scoring/calculate_stop_priority.py

echo "Syntax checks passed."
