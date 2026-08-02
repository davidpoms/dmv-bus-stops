import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
c = conn.cursor()

tables = [
    "physical_stops",
    "improvement_opportunities",
    "opportunity_assessments",
    "stop_observations",
    "stop_consensus",
    "improvement_recommendations",
    "review_queue",
    "stop_review_assignments"
]

for t in tables:
    try:
        count = c.execute(
            f"SELECT COUNT(*) FROM {t}"
        ).fetchone()[0]

        print(f"{t}: {count}")

    except Exception as e:
        print(f"{t}: MISSING ({e})")

conn.close()