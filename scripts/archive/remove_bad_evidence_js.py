from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

start = text.find("function loadEvidenceSummary()")

if start == -1:
    raise SystemExit("Evidence loader not found")

text = text[:start].rstrip() + "\n"

p.write_text(text)

print("Removed bad evidence JS block")
