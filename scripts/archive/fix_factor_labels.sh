#!/bin/bash

set -e

FILE="src/assessment/score_improvement_opportunities.py"

python - <<'PY'
from pathlib import Path

path = Path("src/assessment/score_improvement_opportunities.py")

text = path.read_text()

text = text.replace(
    '"ridership": {',
    '"route_exposure": {'
)

text = text.replace(
    '"total_daily_weekday_boardings":',
    '"combined_route_weekday_boardings":'
)

text = text.replace(
    '"highest_route_daily_boardings":',
    '"highest_route_weekday_boardings":'
)

text = text.replace(
    '"score": 100.0',
    '"score": 100.0'
)

text = text.replace(
    '"note":',
    '"note":'
)

path.write_text(text)

print("Updated factor labels.")
PY

python -m py_compile "$FILE"

echo "Syntax check passed."
