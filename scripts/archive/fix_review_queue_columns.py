from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

text = text.replace(
    "ps.lat,",
    "ps.latitude,"
)

text = text.replace(
    "ps.lon,",
    "ps.longitude,"
)

text = text.replace(
    "ps.location,",
    "ps.primary_name,"
)

path.write_text(text)

print("Fixed review queue physical_stops columns")
