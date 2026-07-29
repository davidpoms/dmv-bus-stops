from pathlib import Path

path = Path("dmv_bus_stops_dashboard.html")

text = path.read_text()

start_marker = """
<h1>DMV Bus Stop Intelligence Volunteer Review Handbook</h1>
"""

start = text.find(start_marker)

if start == -1:
    raise SystemExit("Review handbook not found")


end_marker = """
<h2>
Live Priority Map
</h2>
"""

end = text.find(end_marker, start)

if end == -1:
    raise SystemExit("Live Priority Map marker not found")


text = text[:start] + text[end:]

path.write_text(text)

print("Removed volunteer handbook section")
