from pathlib import Path
from datetime import datetime

path = Path("src/api/app.py")

text = path.read_text()

backup = path.with_suffix(
    ".py.bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
)

backup.write_text(text)

old = """
        query_db(
            \"\"\"
            INSERT INTO stop_review_assignments
            (
                stop_id,
                reviewer_id,
                scenario,
                status
            )
            VALUES
            (?, ?, ?, 'assigned')
            \"\"\",
            (
                stop_id,
                "anonymous",
                scenario
            )
        )
"""

new = """
        query_db(
            \"\"\"
            INSERT INTO stop_review_assignments
            (
                stop_id,
                reviewer_id,
                scenario,
                status
            )
            VALUES
            (?, ?, ?, 'assigned')
            \"\"\",
            (
                stop_id,
                "anonymous",
                scenario
            )
        )


        assignment = query_db(
            \"\"\"
            SELECT
                id,
                reviewer_id,
                stop_id

            FROM stop_review_assignments

            WHERE stop_id=?

            AND status='assigned'

            ORDER BY id DESC

            LIMIT 1
            \"\"\",
            (
                stop_id,
            )
        )
"""

if old not in text:
    print("Could not find insert block")
    exit()

text = text.replace(old, new, 1)

path.write_text(text)

print("Reload after assignment creation fixed")
print("Backup:", backup)