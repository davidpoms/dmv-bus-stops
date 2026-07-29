from pathlib import Path

path = Path("src/dashboard/static/dashboard.js")

text = path.read_text()

trailing = """
// -----------------------------
// Review Queue
// -----------------------------
"""

if not text.rstrip().endswith(trailing.strip()):
    raise SystemExit("Trailing Review Queue comment not found")

text = text.rstrip()

text = text[:text.rfind("// -----------------------------")].rstrip() + "\n"

path.write_text(text)

print("Removed trailing Review Queue comment")
