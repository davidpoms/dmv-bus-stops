#!/bin/bash

set -e

python - <<'PY'
from pathlib import Path

path = Path("src/assessment/generate_improvement_recommendations.py")

text = path.read_text()

text = text.replace(
"""
        SELECT

            o.physical_stop_id,
""",
"""
        SELECT

            o.physical_stop_id,

            io.opportunity_score,
"""
)

text = text.replace(
"""
        FROM stop_observations o

        LEFT JOIN improvement_opportunities io

            ON o.physical_stop_id = io.physical_stop_id;
""",
"""
        FROM stop_observations o

        LEFT JOIN improvement_opportunities io

            ON o.physical_stop_id = io.physical_stop_id;
"""
)

text = text.replace(
"""
        (
            stop_id,
            shelter_present,
""",
"""
        (
            stop_id,
            opportunity_score,
            shelter_present,
"""
)

text = text.replace(
"""
        if not bench_present and bench_feasible:
""",
"""
        if (
            not bench_present
            and bench_feasible
            and opportunity_score
            and opportunity_score >= 70
        ):
"""
)

text = text.replace(
"""
                        "Space appears available"
""",
"""
                        "Space appears available",
                        f"Opportunity score {round(opportunity_score,1)}"
"""
)

text = text.replace(
"""
        if not shelter_present and score and score >= 80:
""",
"""
        if (
            not shelter_present
            and opportunity_score
            and opportunity_score >= 80
        ):
"""
)

path.write_text(text)

print("Updated recommendation generation.")
PY

python -m py_compile src/assessment/generate_improvement_recommendations.py

echo "Syntax check passed."
