import requests
import pandas as pd


URL = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
    "DCGIS_DATA/Transportation_Rail_Bus_WebMercator/"
    "MapServer/53/query"
)

records = []

offset = 0
limit = 2000

while True:
    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "geojson",
        "resultOffset": offset,
        "resultRecordCount": limit,
    }

    r = requests.get(URL, params=params)
    data = r.json()

    features = data["features"]

    print(
        "Downloaded:",
        offset,
        "+",
        len(features)
    )

    if not features:
        break

    records.extend(
        [
            f["properties"]
            for f in features
        ]
    )

    if not data.get("exceededTransferLimit"):
        break

    offset += limit


df = pd.DataFrame(records)

print()
print("Total DCGIS stops:", len(df))

df.to_csv(
    "data/dcgis_wmata_stops.csv",
    index=False
)
