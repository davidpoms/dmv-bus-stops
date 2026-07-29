from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

text = text.replace(
    "Community evidence - shelter:",
    "Automated evidence - shelter:"
)

text = text.replace(
    "Community evidence - bench:",
    "Automated evidence - bench:"
)

p.write_text(text)

print("Renamed automated evidence labels")
