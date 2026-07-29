from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

marker = """
<h2>
Community Review Queue
</h2>


<div id="reviewQueue">

Loading review queue...

</div>
"""

if marker not in text:
    raise SystemExit("bottom queue block not found")

text = text.replace(marker, "")

p.write_text(text)

print("Removed bottom queue")
