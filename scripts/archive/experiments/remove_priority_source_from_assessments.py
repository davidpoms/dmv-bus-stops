import sqlite3
import json

DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)
cursor = conn.cursor()


rows = cursor.execute(
    """
    SELECT
        physical_stop_id,
        assessment_json
    FROM opportunity_assessments
    """
).fetchall()


updates = []


for physical_stop_id, raw in rows:

    if not raw:
        continue

    try:
        data = json.loads(raw)
    except Exception:
        continue


    if "priority_source" in data:

        del data["priority_source"]

        updates.append(
            (
                json.dumps(data),
                physical_stop_id
            )
        )


cursor.executemany(
    """
    UPDATE opportunity_assessments
    SET assessment_json = ?
    WHERE physical_stop_id = ?
    """,
    updates
)


conn.commit()

print(
    f"Removed priority_source from {len(updates)} assessments"
)


conn.close()