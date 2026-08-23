import sqlite3

c = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

print("routes")
print(
    c.execute(
        "select count(*) from routes"
    ).fetchone()
)

print("ridership snapshots")
print(
    c.execute(
        "select count(*) from ridership_snapshots"
    ).fetchone()
)

print("sample routes")
print(
    c.execute(
        "select * from routes limit 5"
    ).fetchall()
)

print("sample ridership")
print(
    c.execute(
        "select * from ridership_snapshots limit 5"
    ).fetchall()
)