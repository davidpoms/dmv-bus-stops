from pathlib import Path

p = Path("scripts/enrich_stops_with_osm.py")

text = p.read_text()

old = """    VALUES (?, ?, ?, ?, ?, ?)
    """,

new = """    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,

if old[0] in text:
    text = text.replace(old[0], new[0])
    print("Updated placeholders")
else:
    print("Placeholder pattern not found")

p.write_text(text)
