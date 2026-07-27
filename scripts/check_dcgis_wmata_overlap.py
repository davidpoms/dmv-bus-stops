import requests
import pandas as pd


URL = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
    "DCGIS_DATA/Transportation_Rail_Bus_WebMercator/"
    "MapServer/53/query"
)


params = {
    "where": "1=1",
    "outFields": "*",
    "f": "geojson",
    "resultRecordCount": 5000
}


r = requests.get(URL, params=params)

print("Status:", r.status_code)

data = r.json()

dc = pd.DataFrame(
    [
        f["properties"]
        for f in data["features"]
    ]
)

print("DCGIS records:", len(dc))
print()

print(dc.columns.tolist())
print()

print(dc.head())


wmata = pd.read_csv(
    "data/wmata_bus_stops_raw.csv"
)


print()
print("WMATA records:", len(wmata))


print()

overlap = set(
    dc.BSTP_GEO_ID.astype(str)
) & set(
    wmata.BSTP_GEO_ID.astype(str)
)

print(
    "BSTP_GEO_ID overlap:",
    len(overlap)
)
