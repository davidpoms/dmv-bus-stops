from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

needle = """
    row = stop[0]


    streetview = get_road_index().nearest_road(
"""

replacement = """
    row = stop[0]


    amenities_wmata = query_db(
        \"\"\"
        SELECT
            wmata_shelter,
            wmata_bench,
            wmata_accessible,
            match_confidence
        FROM stop_wmata_evidence
        WHERE physical_stop_id = ?
        \"\"\",
        (stop_id,)
    )


    amenities_osm = query_db(
        \"\"\"
        SELECT
            osm_shelter,
            osm_bench
        FROM stop_osm_evidence
        WHERE stop_id = ?
        \"\"\",
        (stop_id,)
    )


    amenities = {
        "wmata": (
            {
                "shelter": amenities_wmata[0][0],
                "bench": amenities_wmata[0][1],
                "accessible": amenities_wmata[0][2],
                "confidence": amenities_wmata[0][3]
            }
            if amenities_wmata else None
        ),

        "osm": (
            {
                "shelter": amenities_osm[0][0],
                "bench": amenities_osm[0][1]
            }
            if amenities_osm else None
        )
    }


    streetview = get_road_index().nearest_road(
"""

if needle not in text:
    raise Exception("Insertion point not found")

text=text.replace(
    needle,
    replacement,
    1
)


needle2 = """
            "streetview_url": streetview_url,

            "wmata_evidence":
"""

replacement2 = """
            "streetview_url": streetview_url,

            "amenities": amenities,

            "wmata_evidence":
"""

if needle2 not in text:
    raise Exception("JSON insertion point not found")


text=text.replace(
    needle2,
    replacement2,
    1
)


p.write_text(text)

print(
    "Added amenities to review info endpoint"
)
