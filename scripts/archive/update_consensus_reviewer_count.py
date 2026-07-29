from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

old = """
HAVING COUNT(*) >= 3
"""

new = """
HAVING COUNT(
    DISTINCT COALESCE(
        reviewer_id,
        CAST(user_id AS TEXT),
        anonymous_email
    )
) >= 3
"""

text = text.replace(old,new)

p.write_text(text)

print("Updated consensus reviewer counting")
