import sqlite3

DB = "src/database/dmv_bus_stops.db"

PHYSICAL_STOP_ID = 3765


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

cur = conn.cursor()


print("Current routes:")

rows = cur.execute(
    """
    SELECT
        psm.physical_stop_id,
        bs.id AS bus_stop_id,
        bs.external_stop_id,
        sr.route_id,
        r.route_name

    FROM physical_stop_members psm

    JOIN bus_stops bs
        ON psm.bus_stop_id = bs.id

    JOIN stop_routes sr
        ON bs.id = sr.stop_id

    LEFT JOIN routes r
        ON sr.route_id = r.route_id

    WHERE psm.physical_stop_id = ?
    """,
    (PHYSICAL_STOP_ID,)
).fetchall()


for row in rows:
    print(dict(row))


print("\nRemoving route assignments...")


cur.execute(
    """
    DELETE FROM stop_routes

    WHERE stop_id IN
    (
        SELECT bus_stop_id
        FROM physical_stop_members
        WHERE physical_stop_id = ?
    )
    """,
    (PHYSICAL_STOP_ID,)
)


conn.commit()


print("\nRemaining routes:")

rows = cur.execute(
    """
    SELECT
        sr.stop_id,
        sr.route_id,
        r.route_name

    FROM stop_routes sr

    LEFT JOIN routes r
        ON sr.route_id = r.route_id

    WHERE sr.stop_id IN
    (
        SELECT bus_stop_id
        FROM physical_stop_members
        WHERE physical_stop_id = ?
    )
    """,
    (PHYSICAL_STOP_ID,)
).fetchall()


for row in rows:
    print(dict(row))


conn.close()

print("\nFinished.")