from pathlib import Path

p=Path("src/dashboard/static/dashboard.js")

text=p.read_text()

text=text.replace(
    "<b>Existing stop information</b>",
    "<b>Automated mapping evidence (OpenStreetMap)</b>"
)

text=text.replace(
    "Transit stop confirmed:",
    "Transit stop mapped:"
)

text=text.replace(
    "Automated evidence - shelter:",
    "Shelter mapped:"
)

text=text.replace(
    "Automated evidence - bench:",
    "Bench mapped:"
)

text=text.replace(
    "<b>WMATA-reported stop amenities</b>",
    "<b>WMATA stop inventory</b>"
)

p.write_text(text)

print("Updated popup labels")
