"""
Fix rebuild_stop_consensus.py for current schema.

Changes:
- Join stop_review_assignments to stop_observations using reviewer_id
- Use physical_stop_id instead of nonexistent stop_id in stop_observations
- Require 3 distinct completed reviewers
- Normalize confidence values safely
"""

from pathlib import Path


FILE = Path("scripts/rebuild_stop_consensus.py")


text = FILE.read_text()


# Fix assignment/observation join block
old = """stops = cur.execute(\"\"\"
SELECT
    sr.stop_id

FROM stop_observations sr

JOIN stop_review_assignments a
ON a.stop_id = sr.stop_id

WHERE a.status='completed'

GROUP BY sr.stop_id

HAVING COUNT(
    DISTINCT a.reviewer_id
) >= 3

\"\"\").fetchall()
"""


new = """stops = cur.execute(\"\"\"
SELECT
    a.stop_id

FROM stop_review_assignments a

JOIN stop_observations o
    ON o.physical_stop_id = a.stop_id
    AND o.reviewer_id = a.reviewer_id

WHERE a.status='completed'

GROUP BY a.stop_id

HAVING COUNT(
    DISTINCT a.reviewer_id
) >= 3

\"\"\").fetchall()
"""


if old in text:
    text = text.replace(old, new)
else:
    print("Warning: assignment query block not found")


# Fix observation query
text = text.replace(
"""        FROM stop_observations

        WHERE stop_id=?
""",
"""        FROM stop_observations

        WHERE physical_stop_id=?
"""
)


# Fix confidence handling
text = text.replace(
"""    confidence = sum(
        (r[3] or 0)
        for r in rows
    ) / count
""",
"""    confidences = []

    for r in rows:
        try:
            value = float(r[3])
            confidences.append(value)
        except (TypeError, ValueError):
            pass

    confidence = (
        sum(confidences) / len(confidences)
        if confidences
        else 0.0
    )
"""
)


FILE.write_text(text)

print("Updated rebuild_stop_consensus.py")
