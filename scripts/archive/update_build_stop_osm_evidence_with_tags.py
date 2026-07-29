from pathlib import Path

p = Path("scripts/build_stop_osm_evidence.py")

text = p.read_text()

old = """
    osm_feature_id
)
"""

new = """
    osm_feature_id,
    osm_tags
)
"""

if old not in text:
    raise Exception("Insert column block not found")

text = text.replace(old, new, 1)


old = """
    o.id


FROM physical_stops p
"""

new = """
    o.id,

    o.tags


FROM physical_stops p
"""

if old not in text:
    raise Exception("SELECT block not found")

text = text.replace(old, new, 1)


p.write_text(text)

print("Updated OSM evidence builder with tags")
