import sqlite3
import pandas as pd
import math
from pathlib import Path
from scipy.spatial import cKDTree
import numpy as np


DB = Path("src/database/dmv_bus_stops.db")
INPUT = Path("data/wmata_stops_pipeline.csv")


def distance_m(lat1, lon1, lat2, lon2):
    x = (lon2-lon1)*111320*math.cos(math.radians(lat1))
    y = (lat2-lat1)*110540
    return math.sqrt(x*x+y*y)


def confidence(d):
    if d <= 10:
        return "high"
    elif d <= 75:
        return "medium"
    else:
        return "low"


conn = sqlite3.connect(DB)


physical = pd.read_sql(
    """
    SELECT
        id,
        latitude,
        longitude,
        primary_name
    FROM physical_stops
    """,
    conn
)


wmata = pd.read_csv(INPUT)


matched = pd.read_sql(
    """
    SELECT physical_stop_id
    FROM stop_wmata_evidence
    """,
    conn
)


unmatched = physical[
    ~physical.id.isin(
        matched.physical_stop_id
    )
].copy()


print("Unmatched physical stops:", len(unmatched))


tree = cKDTree(
    wmata[["lat","lon"]].values
)


coords = unmatched[
    ["latitude","longitude"]
].values


distances, indexes = tree.query(
    coords,
    k=1
)


rows = []


for i, (_, stop) in enumerate(unmatched.iterrows()):

    w = wmata.iloc[indexes[i]]

    d = distance_m(
        stop.latitude,
        stop.longitude,
        w.lat,
        w.lon
    )

    # Only accept second-pass matches
    # within relaxed threshold
    if d <= 150:

        rows.append(
            (
                int(stop.id),
                int(w.stop_id),
                w.wmata_status,
                int(w.heading)
                if not pd.isna(w.heading)
                else None,
                w.wmata_bench,
                w.wmata_shelter,
                w.wmata_accessible,
                d,
                confidence(d),
                "WMATA_SECOND_PASS"
            )
        )


print(
    "Second pass matches:",
    len(rows)
)


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

conn.close()

print("Done")
