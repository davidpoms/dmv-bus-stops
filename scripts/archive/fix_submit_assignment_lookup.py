from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
        WHERE id=?
        AND stop_id=?
        AND reviewer_id=?
        AND status='assigned'
"""

new = """
        WHERE id=?
        AND stop_id=?
        AND reviewer_id=?
"""

if old not in text:
    raise SystemExit("Target query not found")

text = text.replace(old, new)

p.write_text(text)

print("Updated submit assignment validation")
