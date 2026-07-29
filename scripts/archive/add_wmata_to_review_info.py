from pathlib import Path

FILE = Path("src/api/app.py")

text = FILE.read_text()

old = """
        SELECT
            id,
            primary_name,
            latitude,
            longitude,
            state,
            dc_ward,
            dc_anc,
            county,
            municipality
        FROM physical_stops
        WHERE id=?
"""

new = """
        SELECT
            p.id,
            p.primary_name,
            p.latitude,
            p.longitude,
            p.state,
            p.dc_ward,
            p.dc_anc,
            p.county,
            p.municipality,

            w.wmata_stop_id,
            w.wmata_status,
            w.wmata_heading,
            w.wmata_bench,
            w.wmata_shelter,
            w.wmata_accessible,
            w.match_distance_m,
            w.match_confidence

        FROM physical_stops p

        LEFT JOIN stop_wmata_evidence w
        ON p.id = w.physical_stop_id

        WHERE p.id=?
"""

if old not in text:
    raise Exception("Could not find review stop SQL block")

text = text.replace(old, new)


old_json = """
            "municipality": row[8]
"""

new_json = """
            "municipality": row[8],

            "wmata": {
                "stop_id": row[9],
                "status": row[10],
                "heading": row[11],
                "bench": row[12],
                "shelter": row[13],
                "accessible": row[14],
                "match_distance_m": row[15],
                "match_confidence": row[16]
            }
"""

if old_json not in text:
    raise Exception("Could not find JSON response block")

text = text.replace(old_json, new_json)

FILE.write_text(text)

print("Added WMATA data to review info endpoint")
