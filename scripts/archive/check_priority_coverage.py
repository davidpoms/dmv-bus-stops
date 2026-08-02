import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
c = conn.cursor()


queries = [
    (
        "Physical stops",
        """
        SELECT COUNT(*)
        FROM physical_stops;
        """
    ),

    (
        "Priority snapshots",
        """
        SELECT COUNT(*)
        FROM stop_priority_snapshots;
        """
    ),

    (
        "Stops with routes",
        """
        SELECT COUNT(DISTINCT physical_stop_id)
        FROM stop_routes;
        """
    ),

    (
        "Stops with ridership snapshots",
        """
        SELECT COUNT(DISTINCT stop_id)
        FROM stop_priority_snapshots
        WHERE factors LIKE '%combined_route_weekday_boardings%';
        """
    )
]


for name, q in queries:
    print(
        name,
        c.execute(q).fetchone()[0]
    )