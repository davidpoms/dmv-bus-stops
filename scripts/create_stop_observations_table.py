import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)

conn.execute("""
CREATE TABLE IF NOT EXISTS stop_observations (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    physical_stop_id INTEGER NOT NULL,

    observer TEXT,

    shelter_present TEXT,
    bench_present TEXT,
    trash_present TEXT,

    bench_feasible TEXT,
    ada_clearance_possible TEXT,

    notes TEXT,

    observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (physical_stop_id)
        REFERENCES physical_stops(id)

);
""")

conn.commit()
conn.close()

print("Created stop_observations table")
