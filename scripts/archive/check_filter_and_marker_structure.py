from pathlib import Path


html = Path(
    "src/dashboard/templates/dashboard.html"
).read_text(
    encoding="utf-8"
)

js = Path(
    "src/dashboard/static/dashboard.js"
).read_text(
    encoding="utf-8"
)


print("\n--- FILTER HTML ---\n")

for line in html.splitlines():
    if (
        "routeFilter" in line
        or "stateFilter" in line
        or "filter" in line.lower()
        or "select" in line.lower()
    ):
        print(line)


print("\n--- MARKER CODE ---\n")

for i,line in enumerate(js.splitlines(),1):
    if (
        "circleMarker" in line
        or "color" in line.lower()
        or "radius" in line.lower()
        or "impact" in line.lower()
        or "priority" in line.lower()
    ):
        print(i, line)