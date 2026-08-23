import requests
import json


SOURCES = {
    "montgomery": {
        "url": "https://gis.montgomerycountymd.gov/arcgis/rest/services/DOT/BusStops/FeatureServer/0/query"
    },
    "arlington": {
        "url": "https://services.arcgis.com/n8kgWFr4EwFGg3zA/arcgis/rest/services/Bus Stops/FeatureServer/0/query"
    },
    "fairfax": {
        "url": "https://www.fairfaxcounty.gov/gisint2/rest/services/DPWES/EAMProductionServ_PGIS/MapServer/22/query"
    },
    "alexandria": {
        "url": "https://geoportal.alexandriava.gov/server/rest/services/Hosted/Bus_Stops/FeatureServer/1/query"
    },
    "prince_georges": {
        "url": "https://gis.princegeorgescountymd.gov/arcgis/rest/services/transportation/Transportation/MapServer/6/query"
    },
}


def inspect_source(name, url):

    print("\n")
    print("=" * 80)
    print(name.upper())
    print(url)
    print("=" * 80)

    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "f": "json",
        "resultRecordCount": 3,
    }

    response = requests.get(url, params=params, timeout=30)

    print("HTTP:", response.status_code)

    data = response.json()

    if "error" in data:
        print("ERROR:")
        print(json.dumps(data["error"], indent=2))
        return

    features = data.get("features", [])

    print("Sample records returned:", len(features))

    if "fields" in data:
        print("\nFIELDS:")
        for field in data["fields"]:
            print(
                f"- {field.get('name')} ({field.get('type')})"
            )

    if features:
        print("\nSAMPLE ATTRIBUTES:")

        for i, feature in enumerate(features[:2], start=1):
            print("\nRecord", i)

            attrs = feature.get("attributes", {})

            for key, value in attrs.items():
                print(f"  {key}: {value}")

        print("\nGEOMETRY SAMPLE:")
        print(
            json.dumps(
                features[0].get("geometry"),
                indent=2
            )
        )


def main():

    for name, source in SOURCES.items():
        try:
            inspect_source(
                name,
                source["url"]
            )

        except Exception as e:
            print(
                f"\nFAILED {name}: {e}"
            )


if __name__ == "__main__":
    main()