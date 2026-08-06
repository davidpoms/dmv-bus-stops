import sqlite3
from pathlib import Path
import pandas as pd
import math


DB = Path("src/database/dmv_bus_stops.db")
INPUT = Path("data/wmata_stops_pipeline.csv")


def distance_m(lat1, lon1, lat2, lon2):
    """
    Approximate distance in meters.
    """
    x = (lon2 - lon1) * 111320 * math.cos(math.radians(lat1))
    y = (lat2 - lat1) * 110540
    return math.sqrt(x*x + y*y)


def confidence(d):
    if d <= 10:
        return "high"
    elif d <= 50:
        return "medium"
    else:
        return "low"


conn = sqlite3.connect(DB)

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


# Load existing WMATA evidence
existing = conn.execute(
    "SELECT COUNT(*) FROM stop_wmata_evidence"
).fetchone()[0]

print("Existing WMATA evidence:", existing)


from scipy.spatial import cKDTree
import numpy as np


rows = []

# Build spatial index once instead of comparing every WMATA stop
# against every physical stop.
physical_coords = physical[["latitude", "longitude"]].values

tree = cKDTree(physical_coords)

wmata_coords = wmata[["lat", "lon"]].values

distances, indexes = tree.query(
    wmata_coords,
    k=1
)

physical_ids = physical["id"].values


for i, (_, w) in enumerate(wmata.iterrows()):

    best_id = int(physical_ids[indexes[i]])

    # Convert approximate degree distance to meters
    best_distance = float(distances[i] * 111320)

    rows.append(
        (
            best_id,
            int(w.stop_id),
            w.wmata_status,
            int(w.heading),
            w.wmata_bench,
            w.wmata_shelter,
            w.wmata_accessible,
            best_distance,
            confidence(best_distance),
            "WMATA"
        )
    )


print("Prepared:", len(rows))


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
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    rows
)


conn.commit()

print("Inserted WMATA evidence:", len(rows))
