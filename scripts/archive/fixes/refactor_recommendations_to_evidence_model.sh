#!/bin/bash

set -e

python - <<'PY'
from pathlib import Path

path = Path("src/assessment/generate_improvement_recommendations.py")

text = path.read_text()

start = text.index("def generate_recommendations():")

end = text.index("\n\nif __name__ == \"__main__\":") 


new_function = r'''
def generate_recommendations():

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()

    setup_table(cursor)

    cursor.execute(
        """
        DELETE FROM improvement_recommendations;
        """
    )


    cursor.execute(
        """
        SELECT

            io.physical_stop_id,

            io.opportunity_score,

            COALESCE(ose.osm_bench,0),

            COALESCE(ose.osm_shelter,0)

        FROM improvement_opportunities io

        LEFT JOIN stop_osm_evidence ose

            ON ose.stop_id = io.physical_stop_id

        ORDER BY io.opportunity_score DESC;

        """
    )


    rows = cursor.fetchall()

    created = 0


    for row in rows:

        (
            stop_id,
            opportunity_score,
            osm_bench,
            osm_shelter
        ) = row


        recommendations = []


        if opportunity_score >= 70 and not osm_bench:

            recommendations.append(
                {
                    "type": "bench_review",
                    "priority": "high",
                    "reasons": [
                        "High route exposure opportunity score",
                        "No bench mapped in OSM",
                        "Volunteer verification needed"
                    ]
                }
            )


        if opportunity_score >= 80 and not osm_shelter:

            recommendations.append(
                {
                    "type": "shelter_review",
                    "priority": "high",
                    "reasons": [
                        "High route exposure opportunity score",
                        "No shelter mapped in OSM",
                        "Shelter opportunity requires review"
                    ]
                }
            )


        for recommendation in recommendations:

            cursor.execute(
                """
                INSERT INTO improvement_recommendations
                (
                    physical_stop_id,
                    recommendation_type,
                    priority,
                    reasons
                )

                VALUES (?, ?, ?, ?);

                """,
                (
                    stop_id,
                    recommendation["type"],
                    recommendation["priority"],
                    json.dumps(
                        recommendation["reasons"]
                    )
                )
            )

            created += 1


    conn.commit()

    conn.close()


    print(
        f"Created {created} improvement recommendations"
    )
'''

text = text[:start] + new_function + text[end:]

path.write_text(text)

print("Refactored recommendation generator.")
PY

python -m py_compile src/assessment/generate_improvement_recommendations.py

echo "Syntax check passed."
