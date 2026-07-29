from pathlib import Path

p = Path("src/review/submit_stop_review.py")

text = p.read_text()

replacements = {
    "Writes field observations into stop_reviews.": "Writes field observations into stop_observations.",
    "INSERT INTO stop_reviews (": "INSERT INTO stop_observations (",
    "stop_id,": "physical_stop_id,",
    "has_shelter,": "shelter_present,",
    "has_bench,": "bench_present,",
    "bench_location_feasible,": "bench_feasible,",
    "reviewer_confidence,": "confidence,",
}

for old, new in replacements.items():
    text = text.replace(old, new)

p.write_text(text)

print("Migrated submit_stop_review to stop_observations")
