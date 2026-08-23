import requests

base = "https://maps2.dcgis.dc.gov/dcgis/rest/services"

folders = [
    "DCGIS_DATA",
    "DDOT",
    "DCGIS_APPS",
    "DCHEALTH",
    "DCOZ",
    "OP",
    "DPW"
]

keywords = [
    "shelter",
    "bench",
    "transit",
    "bus",
    "street",
    "furniture",
    "amenity",
    "facility",
    "asset",
    "stop",
    "sign"
]

for folder in folders:
    url = f"{base}/{folder}"

    r = requests.get(
        url,
        params={"f":"json"}
    ).json()

    for service in r.get("services", []):
        name = service["name"].lower()

        if any(k in name for k in keywords):
            print(folder, "|", service["name"], "|", service["type"])