from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text()

old = """Stops identified:
2,621"""

new = """Stops identified:
{{STOP_COUNT}}"""

if old not in text:
    raise SystemExit("Could not find hardcoded stop count")

path.write_text(text.replace(old, new))

print("Replaced hardcoded stop count placeholder")
