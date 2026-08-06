import requests
import sqlite3

from src.amenities.matcher import haversine_m


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


data = requests.get(
    URL,
    params=params
).json()


features = data["features"]


conn = sqlite3.connect(DB)

stops = conn.execute(
    """
    SELECT
        id,
        latitude,
        longitude
    FROM physical_stops
    """
).fetchall()


distances = []


for feature in features:

    attrs = feature["attributes"]

    lat = attrs.get("Latitude")
    lon = attrs.get("Longitude")

    if lat is None or lon is None:
        continue


    best = None


    for stop in stops:

        d = haversine_m(
            lat,
            lon,
            stop[1],
            stop[2]
        )

        if best is None or d < best:
            best = d


    distances.append(best)


conn.close()


print("DDOT shelters:", len(distances))

print(
    "Within 10m:",
    sum(d <= 10 for d in distances)
)

print(
    "Within 25m:",
    sum(d <= 25 for d in distances)
)

print(
    "Within 50m:",
    sum(d <= 50 for d in distances)
)

print(
    "Within 100m:",
    sum(d <= 100 for d in distances)
)

print(
    "Over 100m:",
    sum(d > 100 for d in distances)
)


print(
    "Largest distances:"
)

for d in sorted(distances, reverse=True)[:20]:
    print(round(d,2))