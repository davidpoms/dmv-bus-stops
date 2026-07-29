from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

text = text.replace(
"""
        SELECT
            bench_location_feasible,
            sun_exposure,
            reviewer_confidence
        FROM stop_reviews
        WHERE stop_id = ?
""",
"""
        SELECT
            bench_feasible,
            NULL,
            confidence
        FROM stop_observations
        WHERE physical_stop_id = ?
"""
)

p.write_text(text)

print("Migrated review-summary endpoint to stop_observations")
