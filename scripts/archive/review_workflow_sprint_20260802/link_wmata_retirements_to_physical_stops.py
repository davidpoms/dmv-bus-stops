import sqlite3
import numpy as np
from scipy.spatial import cKDTree


DB = "src/database/dmv_bus_stops.db"


def haversine_meters(lat1, lon1, lat2, lon2):
    R = 6371000

    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)

    dlat = lat2 - lat1
    dlon = np.radians(lon2 - lon1)

    a = (
        np.sin(dlat / 2) ** 2
        +
        np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    return 2 * R * np.arcsin(np.sqrt(a))


conn = sqlite3.connect(DB)


conn.execute("""
CREATE TABLE IF NOT EXISTS wmata_retirement_links (

    id INTEGER PRIMARY KEY,

    physical_stop_id INTEGER,

    wmata_stop_id TEXT,

    status_code TEXT,

    distance_meters REAL,

    confidence TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")


conn.execute(
    "DELETE FROM wmata_retirement_links"
)


# Load retired WMATA stops
retired = conn.execute("""
SELECT
    wmata_stop_id,
    status_code,
    latitude,
    longitude
FROM wmata_retirement_evidence
""").fetchall()


# Load physical stops
physical = conn.execute("""
SELECT
    id,
    latitude,
    longitude
FROM physical_stops
""").fetchall()


physical_ids = np.array(
    [p[0] for p in physical]
)

physical_coords = np.array(
    [
        [p[1], p[2]]
        for p in physical
    ]
)


# Build KDTree
tree = cKDTree(
    physical_coords
)


rows = []


for wmata_id, status, lat, lon in retired:

    distance, index = tree.query(
        [lat, lon],
        k=1
    )


    matched_id = int(
        physical_ids[index]
    )


    # Convert degree distance approximation to meters
    lat2, lon2 = physical_coords[index]

    meters = haversine_meters(
        lat,
        lon,
        lat2,
        lon2
    )


    if meters <= 20:
        confidence = "high"
    elif meters <= 50:
        confidence = "medium"
    else:
        confidence = "low"


    rows.append(
        (
            matched_id,
            wmata_id,
            status,
            float(meters),
            confidence
        )
    )


conn.executemany(
"""
INSERT INTO wmata_retirement_links
(
physical_stop_id,
wmata_stop_id,
status_code,
distance_meters,
confidence
)
VALUES (?,?,?,?,?)
""",
rows
)


conn.commit()


print(
    "Inserted links:",
    len(rows)
)


print(
    conn.execute("""
    SELECT
        confidence,
        COUNT(*)
    FROM wmata_retirement_links
    GROUP BY confidence
    """).fetchall()
)


conn.close()
