from pathlib import Path
import re

template = Path("src/dashboard/templates/dashboard.html")

text = template.read_text()


# ----------------------------------------------------
# Remove obsolete review.js reference
# ----------------------------------------------------

text = text.replace(
    '<script src="/static/review.js"></script>',
    ''
)

text = text.replace(
    '<script src="static/review.js"></script>',
    ''
)

print("Removed obsolete review.js reference")


# ----------------------------------------------------
# Ensure pipeline table exists before dashboard.js
# ----------------------------------------------------

if "id=\"pipelineBody\"" not in text:

    marker = '<script src="/static/dashboard.js"></script>'

    pipeline = """
<h2>
Review Pipeline Coverage
</h2>

<div class="pipeline-controls">

<button onclick="filterPipeline('')">
All
</button>

<button onclick="filterPipeline('DC Ward')">
DC Wards
</button>

<button onclick="filterPipeline('ANC')">
ANC
</button>

<button onclick="filterPipeline('County')">
Counties
</button>

<button onclick="filterPipeline('Municipality')">
Municipalities
</button>

<input
id="pipelineSearch"
placeholder="Search geography..."
onkeyup="searchPipeline()"
/>

</div>


<table id="pipelineTable">

<thead>
<tr>
<th>Type</th>
<th>Geography</th>
<th>Stops</th>
<th>Queued</th>
<th>Assigned</th>
<th>Reviewed</th>
<th>Consensus</th>
<th>Progress</th>
</tr>
</thead>


<tbody id="pipelineBody">

<tr>
<td colspan="8">
Loading pipeline...
</td>
</tr>

</tbody>

</table>

"""

    text = text.replace(
        marker,
        pipeline + "\n" + marker
    )

    print("Inserted pipeline table")


# ----------------------------------------------------
# Remove duplicate volunteer/map cards
# Keep first volunteer card only
# ----------------------------------------------------

cards = list(re.finditer(
    r'<div class="card volunteer-card">.*?</div>\s*</div>',
    text,
    flags=re.S
))

if len(cards) > 1:

    first_end = cards[0].end()

    for match in reversed(cards[1:]):
        text = text[:match.start()] + text[match.end():]

    print("Removed duplicate volunteer cards")


template.write_text(text)

print("Dashboard template finalized")
