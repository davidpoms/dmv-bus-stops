import sqlite3
from pathlib import Path
import pandas as pd
import math
from scipy.spatial import cKDTree
import numpy as np


DB = Path("src/database/dmv_bus_stops.db")
INPUT = Path("data/wmata_stops_pipeline.csv")

MAX_DISTANCE_METERS = 50


def confidence(d):
    if d <= 10:
        return "high"
    elif d <= 50:
        return "medium"
    return None


def distance_meters(lat1, lon1, lat2, lon2):
    x = (lon2-lon1) * 111320 * math.cos(math.radians(lat1))
    y = (lat2-lat1) * 110540
    return math.sqrt(x*x+y*y)


conn = sqlite3.connect(DB)

print("Clearing old WMATA evidence...")
conn.execute(
    "DELETE FROM stop_wmata_evidence"
)
conn.commit()


wmata = pd.read_csv(INPUT)

physical = pd.read_sql(
    """
    SELECT
        id,
        latitude,
        longitude
    FROM physical_stops
    """,
    conn
)


print("WMATA records:", len(wmata))
print("Physical stops:", len(physical))


coords = physical[
    ["latitude","longitude"]
].values


tree = cKDTree(coords)


wmata_coords = wmata[
    ["lat","lon"]
].values


distances, indexes = tree.query(
    wmata_coords,
    k=1
)


physical_ids = physical["id"].values


rows = []


for i, (_, w) in enumerate(wmata.iterrows()):

    distance = float(
        distances[i] * 111320
    )


    if distance > MAX_DISTANCE_METERS:
        continue


    rows.append(
        (
            int(physical_ids[indexes[i]]),
            int(w.stop_id),
            w.wmata_status,
            int(w.heading),
            w.wmata_bench,
            w.wmata_shelter,
            w.wmata_accessible,
            distance,
            confidence(distance),
            "WMATA"
        )
    )


print("Accepted matches:", len(rows))


conn.executemany(
    """
    INSERT INTO stop_wmata_evidence
    (
        physical_stop_id,
        wmata_stop_id,
        wmata_status,
        wmata_heading,
        wmata_bench,
        wmata_shelter,
        wmata_accessible,
        match_distance_m,
        match_confidence,
        source
    )
    VALUES (?,?,?,?,?,?,?,?,?,?)
    """,
    rows
)


conn.commit()


print("Done")


print(
    conn.execute(
        """
        SELECT
            match_confidence,
            COUNT(*)
        FROM stop_wmata_evidence
        GROUP BY match_confidence
        """
    ).fetchall()
)


conn.close()
