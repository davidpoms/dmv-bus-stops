import sqlite3
from pathlib import Path


DB = Path(
    "src/database/dmv_bus_stops.db"
)


STATUS_PRIORITY = {
    "CONFIRMED_ACTIVE": 6,
    "API_ONLY_ACTIVE_STOP": 5,
    "ROUTE_PRESENT": 4,
    "NO_ROUTE": 3,
    "POSSIBLE_NEW_DDOT_SHELTER": 2,
    "REMOVED_BUT_ROUTE_ACTIVE": 1,
}


STATUS_MAP = {
    "CONFIRMED_ACTIVE": {
        "present": 1,
        "confidence": "high",
    },
    "API_ONLY_ACTIVE_STOP": {
        "present": 1,
        "confidence": "medium",
    },
    "ROUTE_PRESENT": {
        "present": 1,
        "confidence": "medium",
    },
    "NO_ROUTE": {
        "present": 1,
        "confidence": "low",
    },
    "POSSIBLE_NEW_DDOT_SHELTER": {
        "present": 0,
        "confidence": "medium",
    },
    "REMOVED_BUT_ROUTE_ACTIVE": {
        "present": 0,
        "confidence": "high",
    },
}


conn = sqlite3.connect(DB)


rows = conn.execute("""
SELECT
    physical_stop_id,
    ddot_id,
    lifecycle_status,
    confidence,
    notes
FROM stop_ddot_shelter_evidence
""").fetchall()


best = {}


for row in rows:

    physical_stop_id, ddot_id, status, confidence, notes = row

    if status not in STATUS_PRIORITY:
        continue

    if (
        physical_stop_id not in best
        or STATUS_PRIORITY[status]
        >
        STATUS_PRIORITY[
            best[physical_stop_id]["status"]
        ]
    ):

        best[physical_stop_id] = {
            "ddot_id": ddot_id,
            "status": status,
            "confidence": confidence,
            "notes": notes
        }


inserted = 0


for physical_stop_id, record in best.items():

    status = record["status"]

    mapping = STATUS_MAP[status]


    conn.execute("""
    INSERT OR REPLACE INTO stop_amenity_evidence
    (
        physical_stop_id,
        source,
        source_record_id,
        amenity_type,
        present,
        confidence,
        notes,
        value,
        raw_value
    )
    VALUES (?,?,?,?,?,?,?,?,?)
    """,
    (
        physical_stop_id,
        "DDOT",
        record["ddot_id"],
        "shelter",
        mapping["present"],
        mapping["confidence"],
        record["notes"],
        "yes" if mapping["present"] else "no",
        status
    ))

    inserted += 1


conn.commit()
conn.close()


print(
    "Normalized DDOT shelter stops:",
    inserted
)