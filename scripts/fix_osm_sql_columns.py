from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

text = text.replace(
    "osm.get(\"public_bench_evidence\")",
    "osm.get(\"osm_bench\")"
)

text = text.replace(
    "osm.get(\"public_shelter_evidence\")",
    "osm.get(\"osm_shelter\")"
)

text = text.replace(
    "AND public_bench_evidence = 1",
    "AND osm_bench = 1"
)

text = text.replace(
    "AND public_shelter_evidence = 1",
    "AND osm_shelter = 1"
)

p.write_text(text)

print("Fixed OSM SQL column references")
