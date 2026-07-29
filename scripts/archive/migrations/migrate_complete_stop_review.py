from pathlib import Path

p = Path("src/review/complete_stop_review.py")

text = p.read_text()

replacements = {
    "Takes reviewed observations and stores them in stop_reviews.": "Takes reviewed observations and stores them in stop_observations.",
    "DELETE FROM stop_reviews": "DELETE FROM stop_observations",
    "INSERT INTO stop_reviews": "INSERT INTO stop_observations",
    "stop_id,": "physical_stop_id,",
    "has_shelter,": "shelter_present,",
    "has_bench,": "bench_present,",
    "bench_location_feasible,": "bench_feasible,",
}

for old, new in replacements.items():
    text = text.replace(old, new)

p.write_text(text)

print("Migrated complete_stop_review to stop_observations")
