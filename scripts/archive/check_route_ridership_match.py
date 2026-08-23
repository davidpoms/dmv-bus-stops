import sqlite3

c = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

print(
    c.execute(
        """
        SELECT
            r.id,
            r.route_short_name
        FROM routes r
        LIMIT 10
        """
    ).fetchall()
)


print(
    c.execute(
        """
        SELECT
            route_id
        FROM ridership_snapshots
        LIMIT 10
        """
    ).fetchall()
)