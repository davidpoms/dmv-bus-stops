from pathlib import Path

p = Path("src/review/create_stop_reviews.py")

text = p.read_text()

replacements = {
    "create_stop_reviews": "create_stop_observations",
    "stop_reviews": "stop_observations",
    "idx_stop_observations_stop": "idx_stop_observations_stop",
    "stop_id": "physical_stop_id",
    "review_date": "observed_at",
}

for old, new in replacements.items():
    text = text.replace(old, new)

p.write_text(text)

print("Migrated create_stop_reviews to stop_observations")
