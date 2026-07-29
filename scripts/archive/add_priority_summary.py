from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

marker = '<div id="map"></div>'

insert = """
<div id="prioritySummary">

<h3>Investment Priorities</h3>

<div>
<span class="p1">●</span>
P1 Immediate: 75
</div>

<div>
<span class="p2">●</span>
P2 High Value: 672
</div>

<div>
<span class="p3">●</span>
P3 Candidate: 1,874
</div>

<div>
Monitor: 4,886
</div>

</div>

<div id="map"></div>
"""

if marker in text:
    text = text.replace(marker, insert, 1)
    p.write_text(text)
    print("Added priority summary")
else:
    print("Map marker not found")
