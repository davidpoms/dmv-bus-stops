import sqlite3


DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
c = conn.cursor()


print("Views:")
print(
    c.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='view';
        """
    ).fetchall()
)


print("\nDashboard opportunities sample:")


rows = c.execute(
    """
    SELECT *
    FROM dashboard_opportunities
    LIMIT 5;
    """
).fetchall()


for row in rows:
    print(row)