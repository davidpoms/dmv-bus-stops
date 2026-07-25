import sqlite3

DB="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(DB)

checks = [
    (
        "physical stop count",
        "SELECT COUNT(*) FROM physical_stops"
    ),
    (
        "jurisdiction count",
        "SELECT COUNT(*) FROM stop_jurisdiction"
    ),
    (
        "missing states",
        """
        SELECT COUNT(*)
        FROM stop_jurisdiction
        WHERE state IS NULL
        """
    ),
    (
        "DC missing wards",
        """
        SELECT COUNT(*)
        FROM stop_jurisdiction
        WHERE state='DC'
        AND dc_ward IS NULL
        """
    )
]

for name,sql in checks:
    value=conn.execute(sql).fetchone()[0]
    print(f"{name}: {value}")

conn.close()
