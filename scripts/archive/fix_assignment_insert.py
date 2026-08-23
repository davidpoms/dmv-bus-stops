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
"""

new = """
        scenario = request.args.get(
            "mode",
            "opportunity"
        )

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

if old not in text:
    print("Could not find old insert block")
    exit()

text = text.replace(old, new, 1)

path.write_text(text)

print("Fixed assignment insert")
print("Backup:", backup)