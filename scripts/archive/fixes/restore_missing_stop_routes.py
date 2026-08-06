import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

try:
    print("Starting route recovery...")

    conn.execute("BEGIN")

    # Recover from primary backup
    cur.execute("""
    INSERT INTO stop_routes(stop_id, route_id)

    SELECT
        sr.stop_id,
        r.id

    FROM stop_routes_backup sr

    JOIN routes r
        ON r.route_id = sr.route_id

    WHERE NOT EXISTS (
        SELECT 1
        FROM stop_routes existing

        WHERE existing.stop_id = sr.stop_id
        AND existing.route_id = r.id
    )
    """)

    backup_added = cur.rowcount

    print("Recovered from stop_routes_backup:", backup_added)


    # Recover from failed rebuild backup
    cur.execute("""
    INSERT INTO stop_routes(stop_id, route_id)

    SELECT
        sr.stop_id,
        r.id

    FROM stop_routes_failed_rebuild_backup sr

    JOIN routes r
        ON r.route_id = sr.route_id

    WHERE NOT EXISTS (
        SELECT 1
        FROM stop_routes existing

        WHERE existing.stop_id = sr.stop_id
        AND existing.route_id = r.id
    )
    """)

    failed_added = cur.rowcount

    print(
        "Recovered from failed rebuild backup:",
        failed_added
    )


    conn.commit()


    cur.execute("""
    SELECT COUNT(*)
    FROM stop_routes
    """)

    total = cur.fetchone()[0]

    print("New stop_routes total:", total)


except Exception as e:
    conn.rollback()
    print("ERROR - rolled back")
    raise e


finally:
    conn.close()