import sqlite3
import requests
import json
from pathlib import Path


DB = Path("src/database/dmv_bus_stops.db")

URL = "https://data.princegeorgescountymd.gov/resource/b5cd-7mmh.json"


conn = sqlite3.connect(DB)


offset = 0
total = 0


while True:

    params = {
        "$limit": 50000,
        "$offset": offset
    }

    print("Downloading offset", offset)

    r = requests.get(
        URL,
        params=params,
        timeout=120
    )

    data = r.json()

    if not data:
        break


    for row in data:

        geom = row.get("the_geom")

        if not geom:
            continue


        conn.execute(
            """
            INSERT INTO road_centerlines
            (
                source,
                county,
                road_name,
                road_class,
                speed_limit,
                lanes,
                geometry
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "prince_georges",
                "Prince George's",
                row.get("fullname"),
                row.get("rdtype") or row.get("fcc"),
                int(float(row["speed"])) if row.get("speed") else None,
                None,
                json.dumps(geom)
            )
        )


    total += len(data)

    print("Imported", total)

    offset += 50000


conn.commit()

print("Finished Prince George's import:", total)
