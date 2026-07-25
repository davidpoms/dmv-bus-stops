import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS stop_consensus (

    stop_id INTEGER PRIMARY KEY,

    reviewer_count INTEGER NOT NULL,

    has_shelter BOOLEAN,

    has_bench BOOLEAN,

    bench_feasible BOOLEAN,

    ada_accessible BOOLEAN,

    confidence REAL,

    consensus_status TEXT DEFAULT 'pending',

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(stop_id)
        REFERENCES physical_stops(id)

)
""")

conn.commit()

print("Added stop consensus table")

conn.close()
