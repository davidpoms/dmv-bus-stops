from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

start = text.index("<label>\nRoute Filter:")
end = text.index('<div id="map"></div>')

new = """
<label>
Route Filter:
</label>

<select id="routeSelect">
<option value="">
All Routes
</option>
</select>


<div id="routeStatus">
Showing all routes
</div>


<div id="validationPanel">

<h3>Stop Survey Queue</h3>

<p>
Review stops one at a time using Google Street View.
Record conditions at the stop location.
</p>


<div id="validationList">
Loading...
</div>

</div>


<div id="surveyModal" style="
display:none;
position:fixed;
top:10%;
left:10%;
width:80%;
background:white;
border:1px solid black;
padding:20px;
z-index:9999;
">

<div id="surveyContent"></div>

</div>


"""

text = text[:start] + new + text[end:]

# remove old generated summaries
for block in [
    "<h2>\nProject Status",
    "<h2>\nImpact Levels",
    "<h2>\nTop Priority Stops"
]:
    idx = text.find(block)
    if idx != -1:
        text = text[:idx]


p.write_text(text)

print("Rebuilt dashboard template")
