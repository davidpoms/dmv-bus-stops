from pathlib import Path

p = Path("scripts/enrich_stops_with_osm.py")

text = p.read_text()

old = """SELECT id, latitude, longitude
FROM physical_stops"""

new = """SELECT p.id, p.latitude, p.longitude
FROM physical_stops p
LEFT JOIN stop_environment e
    ON p.id = e.stop_id
WHERE e.stop_id IS NULL"""

if old in text:
    text = text.replace(old, new)
else:
    print("SELECT block not found")

p.write_text(text)

print("Added resume logic")
