from pathlib import Path
import re


html_path = Path(
    "src/dashboard/templates/dashboard.html"
)

js_path = Path(
    "src/dashboard/static/dashboard.js"
)


# ----------------------------
# Fix dashboard filter layout
# ----------------------------

html = html_path.read_text(
    encoding="utf-8"
)


bad_block = """<label>
State
<div class="filter-group">

<label for="routeFilter">
Route
</label>

<select id="routeFilter">

<option value="">
All routes
</option>

</select>

</div>


<select id="stateFilter">
<option value="">All</option>
<option value="DC">DC</option>
<option value="Maryland">Maryland</option>
<option value="Virginia">Virginia</option>
</select>
</label>
"""


good_block = """<div class="filter-group">

<label for="routeFilter">
Route
</label>

<select id="routeFilter">

<option value="">
All routes
</option>

</select>

</div>


<div class="filter-group">

<label for="stateFilter">
State
</label>

<select id="stateFilter">
<option value="">All</option>
<option value="DC">DC</option>
<option value="Maryland">Maryland</option>
<option value="Virginia">Virginia</option>
</select>

</div>
"""


if bad_block not in html:
    raise Exception(
        "Could not find exact broken filter block"
    )


html = html.replace(
    bad_block,
    good_block
)


html_path.write_text(
    html,
    encoding="utf-8"
)


print(
    "Fixed filter HTML"
)



# ----------------------------
# Simplify marker styling
# ----------------------------

js = js_path.read_text(
    encoding="utf-8"
)


pattern = re.compile(
    r'let color = "gray";\s*'
    r'let radius = 5;.*?'
    r'const marker = L\.circleMarker',
    re.S
)


replacement = """let color = "gray";
                let radius = 7;


                const marker = L.circleMarker"""
                


if not pattern.search(js):
    raise Exception(
        "Could not find marker block"
    )


js = pattern.sub(
    replacement,
    js,
    count=1
)


# remove priority panes
js = js.replace(
"""
                        pane:
                            props.impact === "very_high"
                            ? "veryHighPriority"
                            :
                            props.impact === "high"
                            ? "highPriority"
                            :
                            "markerPane"
""",
""
)


js_path.write_text(
    js,
    encoding="utf-8"
)


print(
    "Simplified markers"
)

print(
    "Complete"
)