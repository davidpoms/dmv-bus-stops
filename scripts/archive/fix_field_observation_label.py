from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

text = text.replace(
    "Automated evidence - bench:",
    "Field observation - bench present:"
)

p.write_text(text)

print("Fixed field observation label")
