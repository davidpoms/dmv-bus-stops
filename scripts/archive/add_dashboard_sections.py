from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

text = text.replace(
"""
<h2>
Live Priority Map
</h2>
""",
"""
<div class="card">

<h2>
Live Priority Map
</h2>
"""
)

text = text.replace(
"""
<div id="map"></div>
""",
"""
<div id="map"></div>

</div>
"""
)

p.write_text(text)

print("Wrapped map section")
