import sqlite3
import requests


DB = "src/database/dmv_bus_stops.db"


URL = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DDOT/"
    "Planning/FeatureServer/1/query"
)


params = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": 4326,
    "f": "json"
}


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row


rows = requests.get(
    URL,
    params=params
).json()["features"]


print("DDOT assets:", len(rows))


missing = []


for feature in rows:

    a = feature["attributes"]
    geom = feature["geometry"]

    shelter_id = str(
        a.get("DDOT_SHELTER_ID")
    )


    existing = conn.execute(
        """
        SELECT
            physical_stop_id,
            source_record_id
        FROM stop_amenity_evidence
        WHERE source='DDOT'
        AND source_record_id=?
        """,
        (shelter_id,)
    ).fetchone()


    if not existing:

        missing.append(
            {
                "ddot_id": shelter_id,
                "address": a.get("Sales_Address"),
                "lat": geom.get("y"),
                "lon": geom.get("x")
            }
        )


print(
    "Missing DDOT IDs:",
    len(missing)
)


for x in missing[:50]:
    print(x)


conn.close()