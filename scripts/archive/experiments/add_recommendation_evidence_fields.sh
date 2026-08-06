#!/bin/bash

set -e

python - <<'PY'
from pathlib import Path

path = Path("src/assessment/generate_improvement_recommendations.py")

text = path.read_text()

text = text.replace(
"""
            reasons JSON,

            created_at TIMESTAMP
""",
"""
            reasons JSON,

            confidence TEXT,

            evidence JSON,

            created_at TIMESTAMP
"""
)

text = text.replace(
"""
                    reasons
                )

                VALUES (?, ?, ?, ?);
""",
"""
                    reasons,

                    confidence,

                    evidence
                )

                VALUES (?, ?, ?, ?, ?, ?);
"""
)

text = text.replace(
"""
                    json.dumps(
                        recommendation["reasons"]
                    )
                )
""",
"""
                    json.dumps(
                        recommendation["reasons"]
                    ),

                    recommendation["confidence"],

                    json.dumps(
                        recommendation["evidence"]
                    )
                )
"""
)

text = text.replace(
"""
                    "reasons": [
""",
"""
                    "confidence": "medium",

                    "evidence": {
                        "opportunity_score": opportunity_score,
                        "osm_bench": osm_bench,
                        "osm_shelter": osm_shelter
                    },

                    "reasons": [
"""
)

path.write_text(text)

print("Updated recommendation evidence fields.")
PY

python -m py_compile src/assessment/generate_improvement_recommendations.py

echo "Syntax check passed."
