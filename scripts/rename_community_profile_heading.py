from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")

text = text.replace(
    "Your community contribution",
    "Your community profile"
)

path.write_text(
    text,
    encoding="utf-8"
)

print("Renamed community profile heading")