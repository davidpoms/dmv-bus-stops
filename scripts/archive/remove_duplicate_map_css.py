from pathlib import Path

p = Path("src/dashboard/static/dashboard.css")

text = p.read_text()

blocks = text.split("#map {")

if len(blocks) > 2:
    first = "#map {" + blocks[1]
    remainder = "#map {".join(blocks[2:])
    remainder = remainder.split("}", 1)[1] if "}" in remainder else ""
    text = blocks[0] + first + remainder
    p.write_text(text)
    print("Removed duplicate #map CSS")
else:
    print("No duplicate #map CSS found")
