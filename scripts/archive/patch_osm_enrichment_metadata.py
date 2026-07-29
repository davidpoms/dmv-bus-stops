from pathlib import Path

p = Path("scripts/enrich_stops_with_osm.py")

text = p.read_text()

text = text.replace(
"""SELECT id, latitude, longitude
FROM physical_stops
LIMIT 10""",
"""SELECT id, latitude, longitude
FROM physical_stops"""
)

text = text.replace(
"""        tree_cover_score,
        road_class
    )
    VALUES (?, ?, ?, ?, ?, ?)""",
"""        tree_cover_score,
        osm_query_radius_meters,
        osm_source
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
)

text = text.replace(
"""        trees
    ))""",
"""        trees,
        50,
        "Overpass API"
    ))"""
)

p.write_text(text)

print("Patched OSM enrichment metadata")
