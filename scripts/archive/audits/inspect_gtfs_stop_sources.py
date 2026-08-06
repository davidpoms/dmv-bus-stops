import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

targets = [
    245,
    515,
    1374,
    1618,
    2446,
    3376,
    3897,
    3997,
    4967,
    5580,
    6442,
    6557,
    6641,
    7318
]

for stop_id in targets:

    print("\n================")
    print("BUS STOP", stop_id)

    print("GTFS MAP")
    rows = c.execute("""
        SELECT *
        FROM gtfs_stop_map
        WHERE bus_stop_id=?
    """,(stop_id,)).fetchall()

    for r in rows:
        print(dict(r))

    print("BACKUP ROUTES")
    rows = c.execute("""
        SELECT *
        FROM stop_routes_bad_key_backup
        WHERE stop_id=?
    """,(stop_id,)).fetchall()

    for r in rows:
        print(dict(r))