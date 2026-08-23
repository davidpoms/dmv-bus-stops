import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

conn.row_factory = sqlite3.Row
c = conn.cursor()


ids = [
    "1001920",
    "4000377",
    "5002211",
    "5001815",
    "1001481"
]


for gid in ids:

    print("\n================")
    print("GTFS STOP", gid)

    rows = c.execute(
        """
        SELECT *
        FROM gtfs_stop_map
        WHERE gtfs_stop_id=?
        """,
        (gid,)
    ).fetchall()

    for r in rows:
        print(dict(r))


conn.close()