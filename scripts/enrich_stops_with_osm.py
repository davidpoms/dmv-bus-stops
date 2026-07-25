import sqlite3
import requests
from pathlib import Path
import time


DB = Path("src/database/dmv_bus_stops.db")

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter"
]


def query_osm(lat, lon):

    q = f"""
    [out:json];

    (
      way(around:50,{lat},{lon})["highway"="footway"];
      way(around:50,{lat},{lon})["highway"="crossing"];
      way(around:50,{lat},{lon})["building"];
      way(around:50,{lat},{lon})["leisure"="park"];
      way(around:50,{lat},{lon})["natural"="tree"];
    );

    out tags;
    """

    for server in OVERPASS_SERVERS:

        try:
            r = requests.post(
                server,
                data={"data": q},
                headers={
                    "User-Agent": "dmv-bus-stops-research/1.0"
                },
                timeout=60
            )

            if r.status_code == 200:
                return r.json()

            print("OSM server failed:", server, r.status_code)

        except Exception as e:
            print("OSM error:", server, e)

    raise RuntimeError("All Overpass servers failed")


conn = sqlite3.connect(DB)

stops = conn.execute("""
SELECT p.id, p.latitude, p.longitude
FROM physical_stops p
LEFT JOIN stop_environment e
    ON p.id = e.stop_id
WHERE e.stop_id IS NULL
LIMIT 25
""").fetchall()


for stop_id, lat, lon in stops:

    print("Processing", stop_id)

    data = query_osm(lat, lon)

    tags = [
        x.get("tags", {})
        for x in data["elements"]
    ]

    sidewalk = any(
        t.get("highway") == "footway"
        for t in tags
    )

    crossing = any(
        t.get("highway") == "crossing"
        for t in tags
    )

    buildings = sum(
        1
        for t in tags
        if "building" in t
    )

    parks = sum(
        1
        for t in tags
        if t.get("leisure") == "park"
    )

    trees = sum(
        1
        for t in tags
        if t.get("natural") == "tree"
    )


    conn.execute("""
    INSERT OR REPLACE INTO stop_environment
    (
        stop_id,
        sidewalk_nearby,
        crossing_nearby,
        nearby_buildings,
        nearby_parks,
        tree_cover_score
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        stop_id,
        sidewalk,
        crossing,
        buildings,
        parks,
        trees,
        50,
        "Overpass API"
    ))


    conn.commit()

    time.sleep(1)


conn.close()

print("OSM enrichment complete")
