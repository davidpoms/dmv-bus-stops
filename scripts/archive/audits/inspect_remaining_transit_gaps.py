import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()


def dump(rows):
    for row in rows:
        print(dict(row))

ids = [
243,246,511,1331,1564,2345,3085,3212,
3679,3765,4633,5156,5899,6000,6066,6638
]

for pid in ids:
    print("\n================")
    print("PHYSICAL STOP", pid)

    print("\nMEMBERS")
    dump(c.execute("""
        SELECT *
        FROM physical_stop_members
        WHERE physical_stop_id=?
    """,(pid,)).fetchall())

    print("\nBUS STOPS")
    dump(c.execute("""
        SELECT b.*
        FROM physical_stop_members p
        JOIN bus_stops b
          ON p.bus_stop_id=b.id
        WHERE p.physical_stop_id=?
    """,(pid,)).fetchall())

    print("\nTRANSIT EVIDENCE")
    dump(c.execute("""
        SELECT ste.*
        FROM physical_stop_members psm
        JOIN stop_transit_evidence ste
            ON psm.bus_stop_id = ste.stop_id
        WHERE psm.physical_stop_id=?
    """,(pid,)).fetchall())

    print("\nCURRENT ROUTES")
    dump(c.execute("""
        SELECT sr.*
        FROM physical_stop_members psm
        JOIN stop_routes sr
            ON psm.bus_stop_id = sr.stop_id
        WHERE psm.physical_stop_id=?
    """,(pid,)).fetchall())