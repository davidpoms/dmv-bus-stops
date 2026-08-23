import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
cur = conn.cursor()

physical_stop_id = 2415

print("Physical stop members:")
rows = cur.execute(
    """
    SELECT
        psm.physical_stop_id,
        psm.bus_stop_id
    FROM physical_stop_members psm
    WHERE psm.physical_stop_id = ?
    """,
    (physical_stop_id,)
).fetchall()

for row in rows:
    print(row)


print("\nRoutes through physical stop:")
rows = cur.execute(
    """
    SELECT
        r.route_id,
        r.route_name,
        sr.stop_id
    FROM physical_stop_members psm

    JOIN stop_routes sr
        ON sr.stop_id = psm.bus_stop_id

    JOIN routes r
        ON r.route_id = sr.route_id

    WHERE psm.physical_stop_id = ?
    """,
    (physical_stop_id,)
).fetchall()

for row in rows:
    print(row)


conn.close()