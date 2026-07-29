from pathlib import Path

p = Path("scripts/enrich_stops_with_osm.py")

text = p.read_text()

if "import time" not in text:
    text = text.replace(
        "import requests",
        "import requests\nimport time"
    )

if "time.sleep(1)" not in text:
    text = text.replace(
        '    print("Processing", stop_id)',
        '    print("Processing", stop_id)\n\n    time.sleep(1)'
    )

p.write_text(text)

print("Added OSM delay")
