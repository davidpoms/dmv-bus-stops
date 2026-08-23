from pathlib import Path
import re


html_path = Path(
    "src/dashboard/templates/dashboard.html"
)

js_path = Path(
    "src/dashboard/static/dashboard.js"
)


# ----------------------------
# Fix filter HTML
# ----------------------------

html = html_path.read_text(
    encoding="utf-8"
)


pattern = re.compile(
    r'<label>\s*State.*?</select>\s*</label>',
    re.S
)


replacement = """
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


<div class="filter-group">

<label for="stateFilter">
State
</label>

<select id="stateFilter">

<option value="">
All
</option>

<option value="DC">
DC
</option>

<option value="Maryland">
Maryland
</option>

<option value="Virginia">
Virginia
</option>

</select>

</div>
"""


new_html, count = pattern.subn(
    replacement,
    html,
    count=1
)


if count == 0:
    raise Exception(
        "Could not find State filter block"
    )


html_path.write_text(
    new_html,
    encoding="utf-8"
)


print(
    "Fixed filter layout"
)



# ----------------------------
# Fix marker styling
# ----------------------------

js = js_path.read_text(
    encoding="utf-8"
)


# Replace the entire color/radius decision tree

js, count = re.subn(
    r'let color = "gray";\s*let radius = 5;.*?(?=\n\s*const marker = L\.circleMarker)',
    """let color = "gray";
                let radius = 7;

                """,
    js,
    count=1,
    flags=re.S
)


if count == 0:
    raise Exception(
        "Could not simplify marker styling"
    )


# Remove pane logic

js = re.sub(
    r'\s*pane:\s*props\.impact.*?:"markerPane"\s*',
    "",
    js,
    flags=re.S
)


js_path.write_text(
    js,
    encoding="utf-8"
)


print(
    "Simplified marker styling"
)

print(
    "Done"
)