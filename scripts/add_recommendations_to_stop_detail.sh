#!/bin/bash

set -e

python - <<'PY'
from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


old = '''
    projects = query_db(
        """
        SELECT
            recommendation_type,
            project_status

        FROM improvement_projects

        WHERE physical_stop_id = ?;
        """,
        (stop_id,)
    )


    stop_row = stop[0] if stop else None
'''


new = '''
    projects = query_db(
        """
        SELECT
            recommendation_type,
            project_status

        FROM improvement_projects

        WHERE physical_stop_id = ?;
        """,
        (stop_id,)
    )


    recommendations = query_db(
        """
        SELECT
            recommendation_type,
            priority,
            confidence,
            evidence,
            reasons

        FROM improvement_recommendations

        WHERE physical_stop_id = ?

        ORDER BY
            priority,
            recommendation_type;
        """,
        (stop_id,)
    )


    recommendation_payload = []

    for row in recommendations:

        recommendation_payload.append(
            {
                "type": row[0],
                "priority": row[1],
                "confidence": row[2],
                "evidence": json.loads(row[3]) if row[3] else {},
                "reasons": json.loads(row[4]) if row[4] else []
            }
        )


    stop_row = stop[0] if stop else None
'''


if old not in text:
    raise Exception(
        "Could not find insertion point"
    )


text = text.replace(old, new)


old_return = '''
            "projects": [
                {
                    "recommendation": row[0],
                    "status": row[1]
                }
                for row in projects
            ],

            "evidence": evidence,
'''


new_return = '''
            "projects": [
                {
                    "recommendation": row[0],
                    "status": row[1]
                }
                for row in projects
            ],

            "recommendations": recommendation_payload,

            "evidence": evidence,
'''


if old_return not in text:
    raise Exception(
        "Could not find response insertion point"
    )


text = text.replace(
    old_return,
    new_return
)


path.write_text(text)

print(
    "Added recommendations to stop detail endpoint."
)

PY


python -m py_compile src/api/app.py

echo "Syntax check passed."
