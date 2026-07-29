from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

target = """
<div id="map"></div>
"""

replacement = """
<div class="card map-filter-card">

<h2>
Filter the map
</h2>

<div class="filter-row">

<label>
State
<select id="stateFilter">
<option value="">All</option>
<option value="DC">DC</option>
<option value="Maryland">Maryland</option>
<option value="Virginia">Virginia</option>
</select>
</label>


<label>
County
<select id="countyFilter">
<option value="">All</option>
</select>
</label>


<label>
Ward
<select id="wardFilter">
<option value="">All</option>
</select>
</label>


<button id="applyMapFilters">
Apply Filters
</button>

</div>

</div>


<div id="map"></div>
"""

if target not in text:
    raise Exception("Map placeholder not found")

text=text.replace(target,replacement)

p.write_text(text)

print("Map filter card added")
