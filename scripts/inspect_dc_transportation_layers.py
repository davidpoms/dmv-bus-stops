import requests

url = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
    "DCGIS_DATA/Transportation_WebMercator/MapServer"
)

r = requests.get(
    url,
    params={"f": "json"}
).json()

for layer in r.get("layers", []):
    print(layer["id"], layer["name"])