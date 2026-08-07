import requests
import re


URL = (
    "https://gis.montgomerycountymd.gov/arcgis/rest/services/"
    "DOT/BusStops/FeatureServer/0/query"
)


PARAMS = {
    "where": "1=1",
    "outFields": "ROUTES",
    "returnGeometry": "false",
    "f": "json",
    "resultRecordCount": 6000
}


data = requests.get(
    URL,
    params=PARAMS,
    timeout=60
).json()


features = data.get(
    "features",
    []
)


wmata = 0
ride_on = 0
unknown = 0


examples = []


for f in features:

    routes = (
        f["attributes"]
        .get("ROUTES")
        or ""
    )

    tokens = [
        r.strip()
        for r in routes.split(",")
        if r.strip()
    ]


    if any(
        re.search(
            r"[A-Z]",
            r
        )
        for r in tokens
    ):
        wmata += 1

    elif tokens:
        ride_on += 1

    else:
        unknown += 1

    if len(examples) < 20:
        examples.append(routes)


print("Total:", len(features))
print("Likely WMATA:", wmata)
print("Likely Ride On:", ride_on)
print("Unknown:", unknown)

print("\nExamples:")
for e in examples:
    print(e)