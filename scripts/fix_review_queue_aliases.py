from pathlib import Path

path = Path("src/api/app.py")
text = path.read_text()

text = text.replace(
    "ps.latitude,",
    "ps.latitude AS lat,"
)

text = text.replace(
    "ps.longitude,",
    "ps.longitude AS lon,"
)

path.write_text(text)

print("Added lat/lon aliases")
