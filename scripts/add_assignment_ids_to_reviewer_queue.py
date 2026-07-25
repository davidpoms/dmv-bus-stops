from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
            a.stop_id,
            a.status,
"""

new = """
            a.id AS assignment_id,
            a.stop_id,
            a.reviewer_id,
            a.status,
"""

if old in text:
    text = text.replace(old, new, 1)
    print("Added assignment metadata")
else:
    print("Queue SELECT block not found")

p.write_text(text)
