from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


text = text.replace(
    "<b>OSM Evidence</b><br>",
    "<b>Existing stop information</b><br>"
)

text = text.replace(
    "Bus stop mapped:",
    "Transit stop confirmed:"
)

text = text.replace(
    "Shelter:",
    "Shelter appears to exist:"
)

text = text.replace(
    "Bench:",
    "Bench appears to exist:"
)


p.write_text(text)

print(
    "Updated popup evidence language"
)
