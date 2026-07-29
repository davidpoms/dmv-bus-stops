from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

marker = '<div id="map"></div>'

insert = """
<div id="validationPanel">

<h3>Validation Queue</h3>

<div id="validationList">
Loading...
</div>

</div>

""" + marker

if "validationPanel" not in text:
    text = text.replace(marker, insert, 1)
    p.write_text(text)

print("Added validation panel")
