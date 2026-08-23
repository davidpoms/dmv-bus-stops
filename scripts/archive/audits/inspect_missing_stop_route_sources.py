import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

ids = [
245,
248,
515,
1374,
1618,
2446,
3376,
3866,
3897,
3997,
4967,
5580,
6442,
6557,
6641,
7318
]


for stop_id in ids:

    print("\n================")
    print("BUS STOP", stop_id)

    row = c.execute(
        """
        SELECT *
        FROM bus_stops
        WHERE id=?
        """,
        (stop_id,)
    ).fetchone()

    print(dict(row))


    print("\nGTFS MAP")

    print([
        dict(r)
        for r in c.execute(
            """
            SELECT *
            FROM gtfs_stop_map
            WHERE bus_stop_id=?
            """,
            (stop_id,)
        ).fetchall()
    ])


    print("\nALL ROUTE BACKUPS")

    for table in [
        "stop_routes_backup",
        "stop_routes_failed_rebuild_backup",
        "stop_routes_bad_key_backup"
    ]:

        print("\n", table)

        rows = c.execute(
            f"""
            SELECT *
            FROM {table}
            WHERE stop_id=?
            """,
            (stop_id,)
        ).fetchall()

        for r in rows:
            print(dict(r))


conn.close()