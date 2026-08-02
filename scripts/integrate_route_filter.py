from pathlib import Path


# -----------------------------
# dashboard.html
# -----------------------------

html = Path(
    "src/dashboard/templates/dashboard.html"
).read_text(encoding="utf-8")


# Move route selector into filter section
old = """
<div class="route-selector-card">
<h2>Routes</h2>

<select id="routeSelector">
</select>

</div>
"""


new = """
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
"""


if old in html:
    html = html.replace(old, "")


# insert route filter before state filter
needle = """
<select id="stateFilter">
"""

html = html.replace(
    needle,
    new + "\n" + needle
)


Path(
    "src/dashboard/templates/dashboard.html"
).write_text(html, encoding="utf-8")



# -----------------------------
# dashboard.js
# -----------------------------

js_path = Path(
    "src/dashboard/static/dashboard.js"
)

js = js_path.read_text(encoding="utf-8")



# Remove old duplicate route loader block
start = js.find(
"""
fetch("/routes")
"""
)

end = js.find(
"""
const routeSelect =
""",
start
)

if start != -1 and end != -1:
    js = (
        js[:start]
        +
        js[end:]
    )



# Replace routeSelector references
js = js.replace(
    "routeSelector",
    "routeFilter"
)



# Remove old window load loader
js = js.replace(
"""
window.addEventListener(
    "load",
    loadRoutes
);
""",
""
)



# Add route filter handling
insert_after = """
if(routeFilter){

    routeFilter.addEventListener(
        "change",
        function(){

            loadStops(
                this.value
            );

        }
    );

}

"""


marker = """
if(document.getElementById("map")){
"""

if insert_after not in js:
    js = js.replace(
        marker,
        insert_after + "\n" + marker
    )



# Add route to filter collection
old_filter_list = """
[
        "review",
        "state",
"""

new_filter_list = """
[
        "review",
        "route",
        "state",
"""


js = js.replace(
    old_filter_list,
    new_filter_list
)



# Add route loading function
route_loader = r"""

function loadRouteFilter(){

    fetch("/routes")

    .then(
        response => response.json()
    )

    .then(
        routes => {

            const selector =
                document.getElementById(
                    "routeFilter"
                );

            if(!selector){
                return;
            }


            routes.forEach(
                route => {

                    const option =
                        document.createElement(
                            "option"
                        );

                    option.value =
                        route.route_id;


                    option.textContent =
                        route.route_id +
                        " - " +
                        route.route_name;


                    selector.appendChild(
                        option
                    );

                }
            );

        }
    );

}

"""


if "function loadRouteFilter()" not in js:

    js += route_loader


js += """

window.addEventListener(
    "load",
    loadRouteFilter
);

"""


js_path.write_text(js)



print(
    "Route filter integration complete"
)