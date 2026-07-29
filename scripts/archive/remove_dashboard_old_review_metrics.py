from pathlib import Path

path = Path("dmv_bus_stops_dashboard.html")

text = path.read_text()


start_marker = """
<h2>
Consensus Verification Pipeline
</h2>
"""

start = text.find(start_marker)

if start == -1:
    raise SystemExit("Consensus section not found")


end_marker = """
<h2>
Community Review Network
</h2>
"""

end = text.find(end_marker, start)

if end == -1:
    raise SystemExit("Community Review Network marker not found")


text = text[:start] + text[end:]

path.write_text(text)

print("Removed old review metrics")
