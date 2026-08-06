import requests

url = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
    "DDOT/ADA_Assessment/MapServer"
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