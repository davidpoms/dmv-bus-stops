from pathlib import Path

p = Path("scripts/enrich_stops_with_osm.py")

text = p.read_text()

text = text.replace(
    "WHERE e.stop_id IS NULL",
    "WHERE e.stop_id IS NULL\nLIMIT 25"
)

p.write_text(text)

print("Limited OSM batch to 25 stops")
