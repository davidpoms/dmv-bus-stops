from pathlib import Path
import shutil
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]

FILES = [
    ROOT / "src/dashboard/templates/dashboard.html",
    ROOT / "src/dashboard/static/dashboard.js",
]


def backup(path):
    backup = path.with_suffix(
        path.suffix + "." +
        datetime.now().strftime("%Y%m%d%H%M%S") +
        ".bak"
    )

    shutil.copy(path, backup)
    print("Backup:", backup)


def replace_once(path, old, new):
    text = path.read_text(encoding="utf-8")

    if old not in text:
        print("NOT FOUND:", path.name)
        return

    text = text.replace(old, new, 1)

    path.write_text(
        text,
        encoding="utf-8"
    )

    print("Updated:", path.name)


for f in FILES:
    backup(f)


html = ROOT / "src/dashboard/templates/dashboard.html"


replace_once(
    html,
    """
<div class="dashboard-links">
""",
    """
<div class="dashboard-links">

<div class="route-selector-card">

<label>
🚌 My Routes
<select id="routeSelector">
<option value="">All routes</option>
</select>
</label>

</div>

"""
)


js = ROOT / "src/dashboard/static/dashboard.js"


route_js = """


// Route selector

function loadRoutes(){

    fetch("/routes")
    .then(response => response.json())
    .then(routes => {

        const selector =
            document.getElementById(
                "routeSelector"
            );

        if(!selector){
            return;
        }


        routes.forEach(route => {

            const option =
                document.createElement("option");

            option.value =
                route.route_id;

            option.textContent =
                route.route_name;

            selector.appendChild(option);

        });

    });

}



const routeSelector =
    document.getElementById(
        "routeSelector"
    );


if(routeSelector){

    routeSelector.addEventListener(
        "change",
        function(){

            loadStops(
                this.value
            );

        }
    );

}


window.addEventListener(
    "load",
    loadRoutes
);

"""

with js.open("a", encoding="utf-8") as f:
    f.write(route_js)


print("Dashboard phase 1 complete")