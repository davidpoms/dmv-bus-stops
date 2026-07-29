import sqlite3
import requests
from pathlib import Path

DB = Path("src/database/dmv_bus_stops.db")

URL = "https://services1.arcgis.com/ioennV6PpG5Xodq0/arcgis/rest/services/OpenData_A1/FeatureServer/0/query"

conn = sqlite3.connect(DB)

offset = 0
count = 0

while True:

    params = {
        "where": "1=1",
        "outFields": "SEGID,L_JURISDICTION,R_JURISDICTION,MAINT_RES,DATA_SOURCE",
        "f": "geojson",
        "resultOffset": offset,
        "resultRecordCount": 2000
    }

    data = requests.get(URL, params=params, timeout=60).json()

    features = data.get("features", [])

    if not features:
        break

    for f in features:
        p = f["properties"]

        seg = p.get("SEGID")

        if not seg:
            continue

        jurisdiction = (
            p.get("L_JURISDICTION")
            or p.get("R_JURISDICTION")
        )

        owner = p.get("MAINT_RES")

        conn.execute("""
        UPDATE road_centerlines
        SET
            jurisdiction=?,
            road_owner=?
        WHERE source='fairfax'
        AND road_name IS NOT NULL
        """,
        (
            jurisdiction,
            owner
        ))

        count += 1

    offset += len(features)

    print("Processed", offset)


conn.commit()
conn.close()

print("Finished", count)
