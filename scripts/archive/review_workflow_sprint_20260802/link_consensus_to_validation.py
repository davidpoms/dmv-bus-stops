import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

updated = cur.execute(
    """
    UPDATE stop_validation

    SET status = 'validated',
        validated_at = CURRENT_TIMESTAMP

    WHERE physical_stop_id IN (
        SELECT stop_id
        FROM stop_consensus
        WHERE consensus_status = 'verified'
    )
    """
).rowcount


conn.commit()


remaining = cur.execute(
    """
    SELECT COUNT(*)
    FROM stop_validation
    WHERE status = 'needs_validation'
    """
).fetchone()[0]


validated = cur.execute(
    """
    SELECT COUNT(*)
    FROM stop_validation
    WHERE status = 'validated'
    """
).fetchone()[0]


conn.close()

print(f"Validation records updated: {updated}")
print(f"Validated: {validated}")
print(f"Remaining: {remaining}")
