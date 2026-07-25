import sqlite3
import json
import math
from pathlib import Path


DB = Path("src/database/dmv_bus_stops.db")


def distance(lat1, lon1, lat2, lon2):

    R = 6371000

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)

    a = (
        math.sin(dlat/2)**2 +
        math.cos(p1) *
        math.cos(p2) *
        math.sin(dlon/2)**2
    )

    return R * 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1-a)
    )


conn = sqlite3.connect(DB)


stops = conn.execute("""
SELECT
id,
latitude,
longitude
FROM physical_stops
""").fetchall()


roads = conn.execute("""
SELECT
id,
source,
road_name,
road_class,
speed_limit,
lanes,
geometry
FROM road_centerlines
""").fetchall()


print("Stops:",len(stops))
print("Roads:",len(roads))


for stop_id,lat,lon in stops:

    best=None
    best_distance=999999


    for road in roads:

        (
        rid,
        source,
        name,
        road_class,
        speed,
        lanes,
        geometry
        ) = road


        try:
            geom=json.loads(geometry)

            coords=[]

            if geom["type"]=="LineString":
                coords=geom["coordinates"]

            elif geom["type"]=="MultiLineString":
                coords=[
                    c
                    for line in geom["coordinates"]
                    for c in line
                ]


            for point in coords:

                rlon,rlat=point[:2]

                d=distance(
                    lat,
                    lon,
                    rlat,
                    rlon
                )

                if d < best_distance:
                    best_distance=d
                    best=road


        except Exception:
            continue


    if best and best_distance < 100:

        (
        rid,
        source,
        name,
        road_class,
        speed,
        lanes,
        geometry
        )=best


        conn.execute("""
        INSERT OR REPLACE INTO stop_environment
        (
        stop_id,
        road_name,
        road_source,
        road_speed_limit,
        road_lanes
        )
        VALUES (?,?,?,?,?)
        """,
        (
        stop_id,
        name,
        source,
        speed,
        lanes
        ))


    if stop_id % 100 == 0:
        print("Processed",stop_id)


conn.commit()

print("Centerline matching complete")
