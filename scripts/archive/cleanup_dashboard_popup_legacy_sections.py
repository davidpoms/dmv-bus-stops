from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


start_marker = """
                                if (detail.projects.length > 0) {
"""


end_marker = """
                                marker.bindPopup(
                                    popup
                                ).openPopup();
"""


start = text.find(start_marker)

if start == -1:
    print("legacy popup section start not found")
    raise SystemExit(1)


end = text.find(end_marker, start)

if end == -1:
    print("popup bind marker not found")
    raise SystemExit(1)


replacement = """
                                marker.bindPopup(
                                    popup
                                ).openPopup();
"""


text = (
    text[:start]
    + replacement
    + text[end + len(end_marker):]
)


p.write_text(text)

print("legacy popup sections removed")

