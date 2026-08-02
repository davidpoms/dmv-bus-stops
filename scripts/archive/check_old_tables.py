import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
cur = conn.cursor()

for t in [
    "stop_observations",
    "stop_validation",
    "community_actions",
    "stop_improvement_impact"
]:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (t,)
    )
    print(t, "YES" if cur.fetchone() else "NO")

conn.close()