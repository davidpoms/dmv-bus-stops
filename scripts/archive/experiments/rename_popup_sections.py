from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

text = text.replace(
    "<b>WMATA-reported stop amenities</b>",
    "<b>Transit agency data (WMATA)</b>"
)

text = text.replace(
    "<b>Existing stop information</b>",
    "<b>Automated evidence</b>"
)

p.write_text(text)

print("Renamed popup sections")
