from pathlib import Path
import re

p = Path("src/api/app.py")
text = p.read_text()

pattern = re.compile(
    r'VALUES\s*\n\s*\(\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?,\s*\?\s*\)',
    re.MULTILINE,
)

replacement = """VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

new_text, count = pattern.subn(replacement, text, count=1)

if count != 1:
    raise Exception(f"Expected to replace 1 placeholder block, replaced {count}")

p.write_text(new_text)
print("Updated INSERT placeholder count from 24 to 25")
