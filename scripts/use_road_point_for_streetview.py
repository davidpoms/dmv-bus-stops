from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
        f"&viewpoint={row[2]},{row[3]}"
        f"&heading={heading}"
"""

new = """
        f"&viewpoint={road['road_lat']},{road['road_lon']}"
        f"&heading={heading}"
"""

if old not in text:
    raise Exception("Could not find Street View viewpoint")

text = text.replace(old, new)

p.write_text(text)

print("Updated Street View viewpoint")
