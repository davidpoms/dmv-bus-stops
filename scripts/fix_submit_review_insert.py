from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'community_review')
"""

new = """
VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

if old not in text:
    print("Old INSERT pattern not found")
else:
    text = text.replace(old, new)

    old2 = """
            data.get("reviewer_id"),
            data.get("reviewer_confidence")
        )
"""

    new2 = """
            data.get("reviewer_id"),
            data.get("reviewer_confidence"),
            "community_review"
        )
"""

    if old2 in text:
        text = text.replace(old2, new2)

    p.write_text(text)

    print("Fixed review submit INSERT")
