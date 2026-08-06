import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

ids = [
245,248,515,1374,1618,2446,3376,3866,
3897,3997,4967,5580,6442,6557,6641,7318
]

for sid in ids:
    print("\n====================")
    print("BUS STOP", sid)

    print("\nBUS STOP RECORD")
    print(dict(c.execute("""
        SELECT *
        FROM bus_stops
        WHERE id=?
    """,(sid,)).fetchone() or {}))

    print("\nEXISTING STOP ROUTES")
    print([
        dict(r) for r in c.execute("""
            SELECT *
            FROM stop_routes
            WHERE stop_id=?
        """,(sid,))
    ])

    print("\nBACKUP ROUTES")
    print([
        dict(r) for r in c.execute("""
            SELECT *
            FROM stop_routes_backup
            WHERE stop_id=?
        """,(sid,))
    ])

    print("\nFAILED REBUILD ROUTES")
    print([
        dict(r) for r in c.execute("""
            SELECT *
            FROM stop_routes_failed_rebuild_backup
            WHERE stop_id=?
        """,(sid,))
    ])