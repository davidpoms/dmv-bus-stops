import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

c = conn.cursor()

print("Routes with ridership matches:")

print(
    c.execute(
        """
        SELECT
            COUNT(DISTINCT r.route_id)
        FROM routes r
        JOIN ridership_snapshots rs
        ON r.route_id = rs.route_id
        """
    ).fetchone()
)


print("\nSample matches:")

for row in c.execute(
    """
    SELECT
        r.route_id,
        r.route_name,
        rs.weekday_boardings
    FROM routes r
    JOIN ridership_snapshots rs
    ON r.route_id = rs.route_id
    LIMIT 10
    """
):
    print(row)