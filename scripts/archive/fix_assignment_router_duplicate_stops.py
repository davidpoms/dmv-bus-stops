from pathlib import Path

p = Path("src/review/assignment_router.py")

text = p.read_text()

text = text.replace(
"""
AND physical_stop_id NOT IN (
    SELECT stop_id
    FROM stop_review_assignments
    WHERE reviewer_id=?
)
""",
"""
AND physical_stop_id NOT IN (
    SELECT stop_id
    FROM stop_review_assignments
    WHERE status='assigned'
)
"""
)

text = text.replace(
"""
            (
                reviewer_id,
            )
""",
"""
            ()
"""
)

p.write_text(text)

print("Updated router to avoid duplicate active assignments")