from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

text = text.replace(
    "Shelter appears to exist:",
    "Community evidence - shelter:"
)

text = text.replace(
    "Bench appears to exist:",
    "Community evidence - bench:"
)

p.write_text(text)

print("Updated amenity language")
