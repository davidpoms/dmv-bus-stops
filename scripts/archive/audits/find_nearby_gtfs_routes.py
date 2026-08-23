import sqlite3
import math

DB = "src/database/dmv_bus_stops.db"

LAT = 38.80121280462822
LON = -77.18470930572067

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    """
    SELECT
        bs.id,
        bs.external_stop_id,
        bs.latitude,
        bs.longitude,
        bs.stop_name,
        sr.route_id,
        r.route_name

    FROM bus_stops bs

    LEFT JOIN stop_routes sr
        ON bs.id = sr.stop_id

    LEFT JOIN routes r
        ON sr.route_id = r.route_id
    """
).fetchall()


def distance(lat1, lon1, lat2, lon2):
    return math.sqrt(
        (lat1-lat2)**2 +
        (lon1-lon2)**2
    )


matches = []

for r in rows:

    d = distance(
        LAT,
        LON,
        r["latitude"],
        r["longitude"]
    )

    if d < 0.003:
        matches.append(
            (
                d,
                dict(r)
            )
        )


for d, row in sorted(matches)[:50]:
    print(
        round(d*111000,1),
        "meters",
        row
    )


conn.close()