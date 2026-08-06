import sqlite3

DB="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(DB)
conn.row_factory=sqlite3.Row
c=conn.cursor()

for table in [
    "gtfs_stop_map",
    "stop_routes_backup",
    "stop_routes_failed_rebuild_backup",
    "routes",
    "stop_transit_evidence"
]:

    print("\n================")
    print(table)

    try:
        print(
            c.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
        )
    except Exception as e:
        print(e)


print("\nGTFS MAP TARGETS")

ids=[
"1001920",
"4000377",
"5002211",
"5001815",
"1001481"
]

for gid in ids:
    print("\n",gid)

    rows=c.execute("""
    SELECT *
    FROM gtfs_stop_map
    WHERE gtfs_stop_id=?
    """,(gid,)).fetchall()

    for r in rows:
        print(dict(r))


conn.close()