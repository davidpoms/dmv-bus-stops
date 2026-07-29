from pathlib import Path

p = Path("src/dashboard/data.py")

text = p.read_text()

start = text.find("def osm_amenity_metrics():")

if start == -1:
    print("Function not found")
    raise SystemExit

# remove until next def (or EOF)
end = text.find("\ndef ", start + 5)

if end == -1:
    text = text[:start]
else:
    text = text[:start] + text[end+1:]

p.write_text(text)

print("Removed slow OSM metric function")
