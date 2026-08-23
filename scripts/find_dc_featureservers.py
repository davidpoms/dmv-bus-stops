import requests

base = "https://maps2.dcgis.dc.gov/dcgis/rest/services"

for folder in ["DCGIS_DATA", "DDOT", "DCDATA_LEVEL2", "DCGIS_APPS"]:
    url = f"{base}/{folder}"

    r = requests.get(
        url,
        params={"f": "json"}
    ).json()

    print("\n================")
    print(folder)
    print("================")

    for s in r.get("services", []):
        if s["type"] == "FeatureServer":
            print(s["name"])