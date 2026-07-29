from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

marker = '<div id="map"></div>'

insert = """
<div id="validationQueue">

<h3>Validation Queue</h3>

<p>
Model-ranked stops awaiting human confirmation
</p>

<div id="validationList">
Loading...
</div>

</div>


<div id="map"></div>
"""

if marker in text and 'id="validationQueue"' not in text:
    text = text.replace(marker, insert, 1)
    p.write_text(text)
    print("Added validation queue panel")

else:
    print("Panel already exists or marker missing")
