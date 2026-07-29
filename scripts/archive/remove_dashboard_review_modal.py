from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text()


start_marker = '<div id="surveyModal" style="'

end_marker = '<div id="map"></div>'


start = text.find(start_marker)
end = text.find(end_marker)


if start == -1:
    raise SystemExit("Could not find surveyModal block")

if end == -1:
    raise SystemExit("Could not find map div")


new_text = (
    text[:start]
    +
    end_marker
    +
    text[end + len(end_marker):]
)


path.write_text(new_text)

print("Removed dashboard survey modal")
