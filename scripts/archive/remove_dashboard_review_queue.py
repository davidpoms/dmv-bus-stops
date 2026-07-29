from pathlib import Path

path = Path("dmv_bus_stops_dashboard.html")

text = path.read_text()

start_marker = """
<h2>
Community Review Queue
</h2>
"""

start = text.find(start_marker)

if start == -1:
    raise SystemExit("Community Review Queue section not found")


end_marker = """
<script src="/static/dashboard.js"></script>
"""

end = text.find(end_marker, start)

if end == -1:
    raise SystemExit("Dashboard script marker not found")


text = (
    text[:start]
    +
    text[end:]
)

path.write_text(text)

print("Removed dashboard community review queue")
