import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

physical_ids = [
    243,246,511,1331,1564,2345,3085,3212,
    3679,3765,4633,5156,5899,6000,6066,6638
]

for pid in physical_ids:

    print("\n====================")
    print("PHYSICAL STOP", pid)

    members = c.execute("""
        SELECT bus_stop_id
        FROM physical_stop_members
        WHERE physical_stop_id=?
    """,(pid,)).fetchall()

    bus_ids = [r["bus_stop_id"] for r in members]

    print("BUS STOP IDS:", bus_ids)

    print("\nTRANSIT EVIDENCE")
    for row in c.execute("""
        SELECT *
        FROM stop_transit_evidence
        WHERE stop_id IN ({})
    """.format(",".join("?"*len(bus_ids))), bus_ids):
        print(dict(row))


    print("\nCURRENT ROUTES")
    for row in c.execute("""
        SELECT *
        FROM stop_routes
        WHERE stop_id IN ({})
    """.format(",".join("?"*len(bus_ids))), bus_ids):
        print(dict(row))


    print("\nBACKUP ROUTES")
    for row in c.execute("""
        SELECT *
        FROM stop_routes_bad_key_backup
        WHERE stop_id IN ({})
    """.format(",".join("?"*len(bus_ids))), bus_ids):
        print(dict(row))