from pathlib import Path

p = Path("scripts/enrich_stops_with_osm.py")

text = p.read_text()

text = text.replace(
'OVERPASS = "https://overpass-api.de/api/interpreter"',
'''OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter"
]'''
)

old = '''    r = requests.post(
        OVERPASS,
        data=q,
        timeout=60
    )

    return r.json()
'''

new = '''    for server in OVERPASS_SERVERS:

        try:
            r = requests.post(
                server,
                data=q,
                timeout=60
            )

            if r.status_code == 200:
                return r.json()

            print("OSM server failed:", server, r.status_code)

        except Exception as e:
            print("OSM error:", server, e)

    raise RuntimeError("All Overpass servers failed")
'''

if old not in text:
    print("Could not find block")
else:
    text=text.replace(old,new)
    p.write_text(text)
    print("Patched OSM servers")
