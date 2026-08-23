from pathlib import Path
import re
from datetime import datetime

path = Path("src/api/app.py")

text = path.read_text()

backup = path.with_suffix(
    ".py.bak_" +
    datetime.now().strftime("%Y%m%d_%H%M%S")
)

backup.write_text(text)

old = """
def review_assignment(stop_id):
"""

new = """
def review_assignment(stop_id):
"""

# Add creation fallback before "if not assignment:"
needle = """
    if not assignment:
"""

replacement = """
    if not assignment:

        query_db(
            \"\"\"
            INSERT INTO stop_review_assignments
            (
                stop_id,
                reviewer_id,
                status,
                assigned_at
            )
            VALUES
            (?, ?, 'assigned', CURRENT_TIMESTAMP)
            \"\"\",
            (
                stop_id,
                "anonymous"
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

if needle not in text:
    print("Could not find insertion point")
    exit()

text = text.replace(
    needle,
    replacement,
    1
)

path.write_text(text)

print("Updated review assignment creation")
print("Backup:", backup)