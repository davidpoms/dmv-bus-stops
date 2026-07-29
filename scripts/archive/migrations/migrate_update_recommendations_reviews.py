from pathlib import Path

p = Path("src/review/update_recommendations_from_reviews.py")

text = p.read_text()

replacements = {

    "FROM stop_reviews;":
    "FROM stop_observations;",

    "stop_id,":
    "physical_stop_id,",

    "has_shelter,":
    "shelter_present,",

    "has_bench,":
    "bench_present,",

    "bench_location_feasible,":
    "bench_feasible,",

}

for old, new in replacements.items():
    text = text.replace(old, new)

p.write_text(text)

print("Migrated update_recommendations_from_reviews to stop_observations")
