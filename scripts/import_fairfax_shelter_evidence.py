"""
Import Fairfax County shelter inventory into stop_amenity_evidence.

Source:
Fairfax County DPWES EAMProductionServ PGIS shelter inventory

Normalization target:
stop_amenity_evidence

One row per:
physical_stop_id + source + amenity_type

This script is idempotent.
"""

import sqlite3
import requests
import json
from collections import defaultdict
from scipy.spatial import cKDTree
from pyproj import Transformer


DB_PATH = "src/database/dmv_bus_stops.db"

FAIRFAX_URL = (
    "https://www.fairfaxcounty.gov/gisint2/rest/services/"
    "DPWES/EAMProductionServ_PGIS/MapServer/22/query"
)

SOURCE = "FAIRFAX_COUNTY"

MATCH_THRESHOLD_METERS = 250


# Fairfax data is Web Mercator-ish EPSG 2283
# Convert Fairfax coordinates to WGS84
transformer = Transformer.from_crs(
    "EPSG:2283",
    "EPSG:4326",
    always_xy=True
)


# physical stops are stored WGS84
def load_physical_stops(conn):

    rows = conn.execute(
        """
        SELECT
            id,
            latitude,
            longitude
        FROM physical_stops
        """
    ).fetchall()

    ids = []
    coords = []

    for r in rows:
        ids.append(r[0])
        coords.append(
            (
                r[2],
                r[1]
            )
        )

    return ids, coords



def fetch_fairfax():

    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "f": "json"
    }

    response = requests.get(
        FAIRFAX_URL,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    return data.get(
        "features",
        []
    )



def meters_to_degrees(m):

    # approximate conversion
    return m / 111000



def confidence(distance):

    if distance <= 50:
        return "high"

    if distance <= 100:
        return "medium"

    return "low"



def insert_or_update(
    conn,
    stop_id,
    asset_ids,
    distance,
    attrs
):

    existing = conn.execute(
        """
        SELECT id
        FROM stop_amenity_evidence
        WHERE physical_stop_id = ?
        AND source = ?
        AND amenity_type = ?
        """,
        (
            stop_id,
            SOURCE,
            "shelter"
        )
    ).fetchone()


    notes = (
        f"Fairfax shelter inventory. "
        f"Assets: {', '.join(asset_ids)}."
    )

    source_metadata = json.dumps(
        attrs,
        separators=(",", ":")
    )


    if existing:

        conn.execute(
            """
            UPDATE stop_amenity_evidence
            SET
                source_record_id = ?,
                confidence = ?,
                match_distance_m = ?,
                notes = ?,
                jurisdiction = ?,
                value = ?,
                raw_value = ?,
                source_metadata = ?
            WHERE id = ?
            """,
            (
                ",".join(asset_ids),
                confidence(distance),
                distance,
                notes,
                SOURCE,
                "yes",
                "1",
                source_metadata,
                existing[0]
            )
        )

        return "updated"



    conn.execute(
        """
        INSERT INTO stop_amenity_evidence
        (
            physical_stop_id,
            source,
            source_record_id,
            amenity_type,
            present,
            confidence,
            match_distance_m,
            notes,
            jurisdiction,
            value,
            raw_value,
            source_metadata
        )
        VALUES
        (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            stop_id,
            SOURCE,
            ",".join(asset_ids),
            "shelter",
            1,
            confidence(distance),
            distance,
            notes,
            SOURCE,
            "yes",
            "1",
            source_metadata
        )
    )

    return "inserted"



def main():

    conn = sqlite3.connect(
        DB_PATH
    )


    physical_ids, coords = load_physical_stops(
        conn
    )


    tree = cKDTree(
        coords
    )


    features = fetch_fairfax()

    print(
        "Fairfax shelter assets:",
        len(features)
    )


    grouped = defaultdict(list)


    for feature in features:

        attrs = feature.get(
            "attributes",
            {}
        )

        geom = feature.get(
            "geometry"
        )

        if not geom:
            continue


        x = geom["x"]
        y = geom["y"]


        lon, lat = transformer.transform(
            x,
            y
        )


        distance, idx = tree.query(
            (
                lon,
                lat
            )
        )


        # convert rough degree distance to meters
        distance_m = distance * 111000


        if distance_m > MATCH_THRESHOLD_METERS:
            continue


        stop_id = physical_ids[idx]


        asset_id = (
            attrs.get(
                "MSMD_SHELTER_NUM"
            )
            or attrs.get(
                "GISOBJID"
            )
        )


        grouped[stop_id].append(
            (
                asset_id,
                distance_m,
                attrs
            )
        )


    inserted = 0
    updated = 0


    for stop_id, assets in grouped.items():

        asset_ids = [
            str(a[0])
            for a in assets
        ]

        best = min(
            assets,
            key=lambda x: x[1]
        )


        result = insert_or_update(
            conn,
            stop_id,
            asset_ids,
            best[1],
            best[2]
        )


        if result == "inserted":
            inserted += 1

        else:
            updated += 1



    conn.commit()
    conn.close()


    print(
        "Stops matched:",
        len(grouped)
    )

    print(
        "Inserted:",
        inserted
    )

    print(
        "Updated:",
        updated
    )



if __name__ == "__main__":
    main()