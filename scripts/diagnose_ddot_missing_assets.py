import sqlite3
import requests


DB = "src/database/dmv_bus_stops.db"


url = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DDOT/"
    "Planning/FeatureServer/1/query"
)


params = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "false",
    "f": "json"
}


features = requests.get(url, params=params).json()["features"]


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row


existing = {
    str(r["source_record_id"])
    for r in conn.execute("""
        SELECT source_record_id
        FROM stop_amenity_evidence
        WHERE source='DDOT'
        AND amenity_type='shelter'
    """)
}


missing = []


for f in features:

    attrs = f["attributes"]

    shelter_id = attrs.get("DDOT_SHELTER_ID")

    if shelter_id is None:
        continue

    if str(shelter_id) not in existing:
        missing.append(attrs)


print("Missing DDOT shelter records:", len(missing))


for x in missing[:20]:
    print({
        "id": x.get("DDOT_SHELTER_ID"),
        "address": x.get("Sales_Address"),
        "lat": x.get("Latitude"),
        "lon": x.get("Longitude")
    })


conn.close()