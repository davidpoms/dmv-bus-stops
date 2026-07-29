from pathlib import Path


# ----------------------------
# Patch dashboard template
# ----------------------------

template = Path(
    "src/dashboard/templates/dashboard.html"
)

text = template.read_text()


old = """
<label>
Route Filter:
</label>

<select id="routeSelect">
<option value="">
All Routes
</option>
</select>
"""


new = """
<label>
Route:
</label>

<select id="routeSelect">
<option value="">
All Routes
</option>
</select>


<label>
State:
</label>

<select id="stateSelect">
<option value="">
All States
</option>
</select>


<label>
County:
</label>

<select id="countySelect">
<option value="">
All Counties
</option>
</select>


<label>
Municipality:
</label>

<select id="municipalitySelect">
<option value="">
All Municipalities
</option>
</select>


<label>
DC Ward:
</label>

<select id="wardSelect">
<option value="">
All Wards
</option>
</select>
"""


if old in text:
    text = text.replace(old, new)
else:
    print("Template selector block already patched or not found")


template.write_text(text)


# ----------------------------
# Patch dashboard javascript
# ----------------------------

js = Path(
    "src/dashboard/static/dashboard.js"
)

text = js.read_text()


old_function = """
function loadStops(route="", impact="", priority="") {
"""


new_function = """
function loadStops(
    route="",
    impact="",
    priority="",
    state="",
    county="",
    municipality="",
    ward=""
) {
"""


if old_function in text:
    text = text.replace(old_function, new_function)
else:
    print("loadStops signature already patched or not found")


old_url = """
    let url = "/map/stops";


    if (route) {
        url += "?route=" + route;

        if (impact) {
            url += "&impact=" + impact;
        }

        if (priority) {
            url += "&priority=" + priority;
        }
    }

    else if (impact) {
        url += "?impact=" + impact;

        if (priority) {
            url += "&priority=" + priority;
        }
    }

    else if (priority) {
        url += "?priority=" + priority;
    }
"""


new_url = """
    let url = "/map/stops";

    let params = new URLSearchParams();


    if (route) {
        params.append("route", route);
    }

    if (impact) {
        params.append("impact", impact);
    }

    if (priority) {
        params.append("priority", priority);
    }

    if (state) {
        params.append("state", state);
    }

    if (county) {
        params.append("county", county);
    }

    if (municipality) {
        params.append("municipality", municipality);
    }

    if (ward) {
        params.append("dc_ward", ward);
    }


    if ([...params].length > 0) {
        url += "?" + params.toString();
    }
"""


if old_url in text:
    text = text.replace(old_url, new_url)
else:
    print("URL builder already patched or not found")


js.write_text(text)


print("Dashboard geography filter patch complete")
