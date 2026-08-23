import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

c = conn.cursor()

print(
    c.execute(
        """
        SELECT
            physical_stop_id,
            combined_route_weekday_boardings,
            highest_route_weekday_boardings,
            routes_served
        FROM opportunity_assessments
        ORDER BY combined_route_weekday_boardings DESC
        LIMIT 10;
        """
    ).fetchall()
)

conn.close()