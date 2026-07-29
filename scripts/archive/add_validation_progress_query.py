from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

addition = '''

def validation_progress():
    return query(
        """
        SELECT

            ps.id AS stop_id,
            ps.primary_name,

            COUNT(sr.id) AS review_count,

            AVG(sr.reviewer_confidence)
                AS confidence,

            sv.status

        FROM physical_stops ps

        LEFT JOIN stop_reviews sr
            ON ps.id = sr.stop_id

        LEFT JOIN stop_validation sv
            ON ps.id = sv.physical_stop_id

        GROUP BY ps.id

        ORDER BY review_count ASC

        """
    )

'''

if "def validation_progress" not in text:
    text += addition

p.write_text(text)

print("validation progress query added")
