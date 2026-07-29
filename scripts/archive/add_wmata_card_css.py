from pathlib import Path

path = Path("src/dashboard/static/dashboard.css")

text = path.read_text()

css = """

.wmata-confirmed {
    font-weight: bold;
}

.wmata-unavailable {
    font-style: italic;
}

"""

if "wmata-confirmed" not in text:
    text += css

path.write_text(text)

print("Added WMATA card CSS")
