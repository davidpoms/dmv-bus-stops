import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

print("STOP ROUTES")

print(
    conn.execute(
        """
        select *
        from stop_routes
        limit 5
        """
    ).fetchall()
)


print("\nROUTES")

print(
    conn.execute(
        """
        select *
        from routes
        limit 5
        """
    ).fetchall()
)

conn.close()