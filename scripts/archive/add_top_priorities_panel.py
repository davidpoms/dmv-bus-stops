from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

marker = '<div id="map"></div>'

insert = """
<div id="topPriorities">

<h3>
Top Investment Opportunities
</h3>

<div id="topPriorityList">
Loading...
</div>

</div>

<div id="map"></div>
"""

if marker in text:
    text = text.replace(marker, insert, 1)
    p.write_text(text)
    print("Added top priorities panel")
else:
    print("Map marker not found")
