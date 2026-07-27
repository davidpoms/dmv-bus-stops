from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

replacements = {
    "No OSM bench evidence":
        "No public data evidence of bench",

    "No OSM shelter evidence":
        "No public data evidence of shelter",

    '"osm_bench":':
        '"public_bench_evidence":',

    '"osm_shelter":':
        '"public_shelter_evidence":',

    "osm_bench":
        "public_bench_evidence",

    "osm_shelter":
        "public_shelter_evidence",
}


for old, new in replacements.items():
    text = text.replace(old, new)


p.write_text(text)

print("Updated public evidence labels")

