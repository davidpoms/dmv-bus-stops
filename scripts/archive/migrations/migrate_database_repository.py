from pathlib import Path

p = Path("src/database/repository.py")

text = p.read_text()

text = text.replace(
    "INSERT INTO stop_reviews",
    "INSERT INTO stop_observations"
)

text = text.replace(
    """
                stop_id,
                has_shelter,
                has_bench,
                reviewer_confidence,
                notes
""",
    """
                physical_stop_id,
                shelter_present,
                bench_present,
                confidence,
                notes
"""
)

text = text.replace(
    """
                review["stop_id"],

                review.get(
                    "shelter_present"
                ),

                review.get(
                    "bench_present"
                ),

                review.get(
                    "review_confidence"
                ),
""",
    """
                review["stop_id"],

                review.get(
                    "shelter_present"
                ),

                review.get(
                    "bench_present"
                ),

                review.get(
                    "review_confidence"
                ),
"""
)

text = text.replace(
    "FROM stop_reviews",
    "FROM stop_observations"
)

text = text.replace(
    "WHERE stop_id = ?",
    "WHERE physical_stop_id = ?"
)

p.write_text(text)

print("Migrated database repository to stop_observations")
