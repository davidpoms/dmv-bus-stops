from pathlib import Path
import re

p = Path("src/api/app.py")

text = p.read_text()

pattern = re.compile(
    r'\nif __name__ == "__main__":\s*\n\s*app\.run\([\s\S]*?\n\s*\)\s*\n?$'
)

match = pattern.search(text)

if not match:
    raise SystemExit("Could not find app.run block")

block = match.group(0)

text = text[:match.start()] + "\n"

text = text.rstrip() + "\n\n" + block.strip() + "\n"

p.write_text(text)

print("Moved app.run block to bottom")
