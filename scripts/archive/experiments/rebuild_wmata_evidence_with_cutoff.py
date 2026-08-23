import sqlite3
from pathlib import Path
import pandas as pd
import math
from scipy.spatial import cKDTree


DB = Path(
    "src/database/dmv_bus_stops.db"
)

INPUT = Path(
    "data/wmata_stops_pipeline.csv"
)


def meters(lat1, lon1, lat2, lon2):

    x = (
        (lon2-lon1)
        *111320
        *math.cos(math.radians(lat1))
    )

    y = (
        (lat2-lat1)
        *110540
    )

    return (x*x+y*y)**0.5



def confidence(d):

    if d <= 10:
        return "high"

    if d <= 50:
        return "medium"

    return "low"



conn = sqlite3.connect(DB)


print("Deleting old WMATA evidence")

conn.execute(
    "DELETE FROM stop_wmata_evidence"
)


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



tree = cKDTree(
    physical[
        ["latitude","longitude"]
    ].values
)


coords = wmata[
    ["lat","lon"]
].values


distances, indexes = tree.query(
    coords,
    k=1
)



rows=[]


physical_ids = physical.id.values


for i,w in wmata.iterrows():

    physical_id = physical_ids[indexes[i]]

    d = distances[i] * 111320


    # Reject bad matches
    if d > 75:
        continue


    rows.append(
        (
            int(physical_id),
            int(w.stop_id),
            w.wmata_status,
            int(w.heading),
            w.wmata_bench,
            w.wmata_shelter,
            w.wmata_accessible,
            float(d),
            confidence(d),
            "WMATA"
        )
    )



print(
    "Keeping matches:",
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

print("Done")

conn.close()
