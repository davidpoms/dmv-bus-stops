from pathlib import Path

path = Path(
    "src/review/assignment_router.py"
)

text = path.read_text()


text = text.replace(
"""        WHERE reviewer_id=?
        AND status='assigned'
""",
"""        WHERE reviewer_id=?
        AND scenario=?
        AND status='assigned'
"""
)


text = text.replace(
"""        (
            reviewer_id,
        )
""",
"""        (
            reviewer_id,
            scenario
        )
"""
)


path.write_text(text)

print(
    "✓ Updated assignment reuse to respect scenario"
)
