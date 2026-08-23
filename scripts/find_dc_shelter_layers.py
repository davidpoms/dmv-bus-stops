import requests

folders = [
    "DCGIS_DATA",
    "DDOT",
    "DCGIS_APPS"
]

keywords = [
    "shelter",
    "bus",
    "transit",
    "bench",
    "amenity",
    "furniture"
]

base = "https://maps2.dcgis.dc.gov/dcgis/rest/services"

for folder in folders:
    url = f"{base}/{folder}"

    r = requests.get(
        url,
        params={"f":"json"}
    ).json()

    print("\nFOLDER:", folder)

    for s in r.get("services", []):

        name = s["name"].lower()

        if any(k in name for k in keywords):
            print(
                "SERVICE:",
                s["name"],
                s["type"]
            )