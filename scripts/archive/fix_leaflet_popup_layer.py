from pathlib import Path


js_path = Path(
    "src/dashboard/static/dashboard.js"
)

js = js_path.read_text(
    encoding="utf-8"
)


old = """
if(document.getElementById("map")){
    loadStops();
}
"""


new = """
if(document.getElementById("map")){

    map.createPane("markerPane");

    map.getPane("markerPane").style.zIndex = 400;

    map.getPane("popupPane").style.zIndex = 700;

    loadStops();
}
"""


if old not in js:
    raise Exception(
        "Could not find map initialization block"
    )


js = js.replace(
    old,
    new
)


js_path.write_text(
    js,
    encoding="utf-8"
)


print(
    "Leaflet popup layering fixed."
)