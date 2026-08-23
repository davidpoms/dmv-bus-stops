import sqlite3


DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
c = conn.cursor()


queries = [

    (
        "Stops with route mappings",
        """
        SELECT COUNT(DISTINCT stop_id)
        FROM stop_routes;
        """
    ),

    (
        "Stops with priority snapshots",
        """
        SELECT COUNT(DISTINCT stop_id)
        FROM stop_priority_snapshots;
        """
    ),

    (
        "Stops missing snapshots",
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT stop_id
            FROM stop_routes

            EXCEPT

            SELECT DISTINCT stop_id
            FROM stop_priority_snapshots
        );
        """
    ),

    (
        "Example missing stops",
        """
        SELECT DISTINCT stop_id
        FROM stop_routes

        EXCEPT

        SELECT DISTINCT stop_id
        FROM stop_priority_snapshots

        LIMIT 10;
        """
    )

]


for name, query in queries:

    print("\n" + name)

    rows = c.execute(query).fetchall()

    for row in rows:
        print(row)