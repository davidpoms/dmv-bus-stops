from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = """
        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

new = """
        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

if old not in text:
    raise SystemExit(
        "Could not find 23-placeholder VALUES block"
    )

text = text.replace(old, new)

path.write_text(text)

print(
    "Fixed /review/submit placeholder count"
)
