import requests

url = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
    "DDOT/ADA_Assessment/MapServer/4"
)

r = requests.get(
    url,
    params={"f":"json"}
).json()

print("NAME:")
print(r.get("name"))

print("\nFIELDS")
print("================")

for field in r.get("fields", []):
    print(
        field["name"],
        "-",
        field.get("alias")
    )