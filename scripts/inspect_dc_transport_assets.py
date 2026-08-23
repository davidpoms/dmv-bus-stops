import requests
import json

url = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
    "DCGIS_DATA/Transportation_Assets_WebMercator/MapServer"
)

r = requests.get(
    url,
    params={"f":"json"}
).json()

print("LAYERS")
print("================")

for layer in r.get("layers", []):
    print(layer["id"], layer["name"])

print("\nTABLES")
print("================")

for table in r.get("tables", []):
    print(table["id"], table["name"])