from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
        VALUES
        (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
"""

new = """
        VALUES
        (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
"""

if old not in text:
    raise Exception("Could not find placeholder block")

text = text.replace(old, new, 1)

p.write_text(text)

print("Fixed submit_review placeholder count")
