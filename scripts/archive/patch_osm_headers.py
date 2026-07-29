from pathlib import Path

p = Path("scripts/enrich_stops_with_osm.py")

text = p.read_text()

old = """            r = requests.post(
                server,
                data=q,
                timeout=60
            )
"""

new = """            r = requests.post(
                server,
                data={"data": q},
                headers={
                    "User-Agent": "dmv-bus-stops-research/1.0"
                },
                timeout=60
            )
"""

if old not in text:
    print("Could not find request block")
else:
    text = text.replace(old, new)
    p.write_text(text)
    print("Patched Overpass request headers")
