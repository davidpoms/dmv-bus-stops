cursor.execute(
    "PRAGMA table_info(bus_stops);"
)

for row in cursor.fetchall():
    print(row)
