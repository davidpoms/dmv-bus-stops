from pathlib import Path

path = Path("dmv_bus_stops_dashboard.html")

text = path.read_text()

text = text.replace(
    'href="static/dashboard.css"',
    'href="/static/dashboard.css"'
)

path.write_text(text)

print("Fixed dashboard CSS path")
