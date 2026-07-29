from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''
            "streetview_url": streetview_url,

            "wmata_evidence": {
'''

new = '''
            "streetview_url": streetview_url,

            "wmata": {
                "availability":
                    "confirmed"
                    if row[9]
                    else "unavailable",

                "stop_id": row[9],
                "status": row[10],
                "bench": row[12],
                "shelter": row[13],
                "accessible": row[14],
                "match_distance_m": row[15],
                "match_confidence": row[16]
            },

            "wmata_evidence": {
'''

if old not in text:
    raise Exception(
        "Could not find JSON insertion point"
    )

text = text.replace(old,new,1)

p.write_text(text)

print(
    "Added review page WMATA compatibility object"
)
