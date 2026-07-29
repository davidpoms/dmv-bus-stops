from pathlib import Path

p = Path("scripts/enrich_stops_with_osm.py")

text = p.read_text()

text = text.replace(
"""FROM physical_stops
LIMIT 10
""",
"""FROM physical_stops
WHERE id NOT IN (
    SELECT stop_id
    FROM stop_environment
)
LIMIT 25
"""
)

old = """    INSERT OR REPLACE INTO stop_environment
    (
        stop_id,
        sidewalk_nearby,
        crossing_nearby,
        nearby_buildings,
        nearby_parks,
        tree_cover_score
    )
    VALUES (?, ?, ?, ?, ?, ?)
"""

new = """    INSERT OR REPLACE INTO stop_environment
    (
        stop_id,
        sidewalk_nearby,
        crossing_nearby,
        nearby_buildings,
        nearby_parks,
        tree_cover_score,
        osm_query_radius_meters,
        osm_source
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

text = text.replace(old, new)

text = text.replace(
"""        trees
    ))
""",
"""        trees,
        50,
        "overpass"
    ))
"""
)

p.write_text(text)

print("Patched OSM enrichment batching")
