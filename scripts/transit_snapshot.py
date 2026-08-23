import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("\nTRANSIT DATA SNAPSHOT")
print("====================")

tables = [
    "bus_stops",
    "physical_stops",
    "gtfs_stop_map",
    "stop_routes",
    "routes",
    "stop_transit_evidence",
    "gtfs_orphan_route_audit",
]

for table in tables:
    try:
        count = cur.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table}: {count}")

    except sqlite3.OperationalError:
        print(f"{table}: missing")


print("\nActive route links:")
print(
    cur.execute(
        """
        SELECT COUNT(*)
        FROM stop_routes
        """
    ).fetchone()[0]
)


print("\nGTFS stops without routes:")
print(
    cur.execute(
        """
        SELECT COUNT(*)
        FROM bus_stops b
        LEFT JOIN stop_routes sr
            ON b.id = sr.stop_id
        WHERE sr.stop_id IS NULL
        """
    ).fetchone()[0]
)


print("\nTransit evidence mismatches:")
print(
    cur.execute(
        """
        SELECT COUNT(*)
        FROM stop_transit_evidence e
        JOIN (
            SELECT
                stop_id,
                COUNT(*) AS route_count
            FROM stop_routes
            GROUP BY stop_id
        ) r
        ON e.stop_id = r.stop_id
        WHERE e.route_count != r.route_count
        """
    ).fetchone()[0]
)


conn.close()