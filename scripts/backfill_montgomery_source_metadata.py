import sqlite3
import json
import requests

DB = "src/database/dmv_bus_stops.db"

URL = (
    "https://gis.montgomerycountymd.gov/arcgis/rest/services/"
    "DOT/BusStops/FeatureServer/0/query"
)

PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "returnTrueCurves": "false",
    "outSR": "4326",
    "f": "json"
}

conn = sqlite3.connect(DB)

existing_ids = {
    str(row[0])
    for row in conn.execute("""
        SELECT DISTINCT source_record_id
        FROM stop_amenity_evidence
        WHERE source = 'MONTGOMERY_COUNTY_WMATA'
    """)
}

print("Existing Montgomery source records:", len(existing_ids))

all_features = []
offset = 0
page_size = 2000

while True:
    print(f"Fetching records {offset}-{offset + page_size - 1}")

    params = PARAMS.copy()
    params.update({
        "resultOffset": offset,
        "resultRecordCount": page_size
    })

    response = requests.get(
        URL,
        params=params,
        timeout=60
    )
    response.raise_for_status()

    data = response.json()
    page = data.get("features", [])

    all_features.extend(page)

    if len(page) < page_size:
        break

    offset += page_size

print("County records fetched:", len(all_features))

updated_rows = 0
updated_records = 0
missing_records = []

for feature in all_features:

    attrs = feature.get("attributes", {})
    stopid = attrs.get("STOPID")

    if stopid is None:
        continue

    stopid = str(stopid)

    if stopid not in existing_ids:
        continue

    geometry = feature.get("geometry") or {}

    source_lat = geometry.get("y")
    source_lon = geometry.get("x")

    metadata = dict(attrs)
    metadata["source_lat"] = source_lat
    metadata["source_lon"] = source_lon

    metadata_json = json.dumps(
        metadata,
        separators=(",", ":")
    )

    cursor = conn.execute("""
        UPDATE stop_amenity_evidence
        SET source_metadata = ?
        WHERE source = 'MONTGOMERY_COUNTY_WMATA'
          AND source_record_id = ?
    """, (
        metadata_json,
        stopid
    ))

    if cursor.rowcount > 0:
        updated_records += 1
        updated_rows += cursor.rowcount

    conn.commit()

print()
print("=== BACKFILL COMPLETE ===")
print("Source records updated:", updated_records)
print("Evidence rows updated:", updated_rows)

remaining = conn.execute("""
    SELECT COUNT(*)
    FROM stop_amenity_evidence
    WHERE source = 'MONTGOMERY_COUNTY_WMATA'
      AND source_metadata IS NULL
""").fetchone()[0]

print("Rows still missing metadata:", remaining)

conn.close()
