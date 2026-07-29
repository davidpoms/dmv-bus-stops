from pathlib import Path
import re

p = Path("src/api/app.py")
text = p.read_text()

pattern = re.compile(
    r"VALUES\s*\(\s*\?[\s\S]*?\)",
    re.MULTILINE
)

match = pattern.search(text)

if not match:
    raise Exception("Could not locate VALUES placeholder block")

new_block = """
VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

text = text[:match.start()] + new_block + text[match.end():]

p.write_text(text)

print("Updated INSERT placeholder count to 25")
