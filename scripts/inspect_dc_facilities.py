import requests

for service in [
    "Facility_and_Structure_WebMercator",
    "Facility_and_Structure"
]:

    url = (
        "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
        f"DCGIS_DATA/{service}/MapServer"
    )

    r = requests.get(
        url,
        params={"f":"json"}
    ).json()

    print("\n================")
    print(service)
    print("================")

    for layer in r.get("layers", []):
        print(layer["id"], layer["name"])

    print("\nTABLES")
    for table in r.get("tables", []):
        print(table["id"], table["name"])