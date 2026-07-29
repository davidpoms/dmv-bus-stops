from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text()

old = """
<h2>
Pipeline Coverage
</h2>
"""

new = """
<h2>
Stop Improvement Pipeline
</h2>
"""

if old not in text:
    raise SystemExit("Pipeline heading not found")

text = text.replace(old,new)

path.write_text(text)

print("Renamed pipeline heading")
