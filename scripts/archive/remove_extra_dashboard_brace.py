from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
  );
 
  }
 
fetch(
"""

new = """
  );
 
fetch(
"""

if old not in text:
    raise SystemExit("target block not found")

text = text.replace(old, new, 1)

p.write_text(text)

print("removed extra dashboard brace")
