from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()


old = """
<th>Type</th>
<th>Geography</th>
<th>Stops</th>
<th>Queued</th>
<th>Assigned</th>
<th>Reviewed</th>
<th>Consensus</th>
<th>Progress</th>
"""


new = """
<th>Type</th>
<th>Geography</th>
<th>Stops</th>
<th>Queued</th>
<th>Reviewed</th>
<th>Consensus</th>
<th>WMATA Evidence</th>
<th>OSM Benches</th>
<th>OSM Shelters</th>
<th>Progress</th>
"""


if old not in text:
    raise SystemExit("Pipeline header not found")


text=text.replace(old,new)

p.write_text(text)

print("Updated pipeline columns")
