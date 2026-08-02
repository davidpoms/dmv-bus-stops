import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
cur = conn.cursor()

for table in [
    "stop_jurisdiction",
    "dc_ward_summary",
    "dc_anc_summary",
    "county_summary",
    "municipality_summary"
]:
    print(table, end=": ")
    result = cur.execute(
        "SELECT name FROM sqlite_master WHERE name=?",
        (table,)
    ).fetchone()
    print("YES" if result else "NO")

conn.close()