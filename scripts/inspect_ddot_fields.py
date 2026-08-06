import requests


url = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DDOT/"
    "Planning/FeatureServer/1/query"
)


params = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "false",
    "resultRecordCount": 5,
    "f": "json"
}


data = requests.get(
    url,
    params=params
).json()


for feature in data["features"]:

    print("\n--- RECORD ---")

    for k, v in feature["attributes"].items():
        print(
            k,
            "=",
            v
        )