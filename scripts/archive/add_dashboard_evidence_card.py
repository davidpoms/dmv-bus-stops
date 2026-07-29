from pathlib import Path

path=Path("src/dashboard/templates/dashboard.html")

text=path.read_text()

marker="<h2>Community Review Network</h2>"

if marker not in text:
    raise SystemExit("marker not found")


card="""

<div class="card">

<h2>
Existing Infrastructure Evidence
</h2>

<p>
These are preliminary estimates from WMATA and OpenStreetMap data.
They are separate from community-verified observations.
</p>

<p>
Likely shelters:
<span id="likelyShelter">
Loading...
</span>
</p>

<p>
Likely benches:
<span id="likelyBench">
Loading...
</span>
</p>

<p>
Stops without shelter evidence:
<span id="noShelterEvidence">
Loading...
</span>
</p>

</div>


"""


text=text.replace(marker, card+marker)

path.write_text(text)

print("Added evidence card")
