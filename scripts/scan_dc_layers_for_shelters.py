import requests

base = "https://maps2.dcgis.dc.gov/dcgis/rest/services"

services = [
    "DCGIS_DATA/Transportation_Signs_Signals_Lights_WebMercator",
    "DCGIS_DATA/Transportation_Rail_Bus_WebMercator",
    "DCGIS_DATA/Transportation_WebMercator",
    "DDOT/DdotAssets",
    "DDOT/Signworks",
    "DDOT/BikeAssets",
]

keywords = [
    "shelter",
    "bus",
    "bench",
    "transit",
    "amen",
    "asset"
]

for service in services:

    url = f"{base}/{service}/MapServer"

    r = requests.get(
        url,
        params={"f":"json"}
    ).json()

    print("\n================")
    print(service)
    print("================")

    for layer in r.get("layers", []):

        name = layer["name"].lower()

        if any(k in name for k in keywords):
            print(
                layer["id"],
                layer["name"]
            )

    for table in r.get("tables", []):

        name = table["name"].lower()

        if any(k in name for k in keywords):
            print(
                "TABLE",
                table["id"],
                table["name"]
            )