from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

# Replace old geography tables section
start = text.find("<h2>Geography Coverage</h2>")

if start == -1:
    # fallback based on first table
    start = text.find("<table")

end = text.find('<script src="static/dashboard.js"></script>')

if start == -1 or end == -1:
    raise Exception("Could not locate dashboard table section")

replacement = """

<h2>
Pipeline Coverage
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


<div class="pipeline-table-container">

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

</div>


<h2>
Community Review Queue
</h2>


<div id="reviewQueue">

Loading review queue...

</div>


"""


text = text[:start] + replacement + text[end:]

text = text.replace(
    '<script src="static/dashboard.js"></script>',
    '<script src="/static/dashboard.js"></script>'
)

p.write_text(text)

print("Dashboard tables replaced")
