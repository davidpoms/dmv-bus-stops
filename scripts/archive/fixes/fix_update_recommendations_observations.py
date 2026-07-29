from pathlib import Path

p = Path("src/review/update_recommendations_from_reviews.py")

text = p.read_text()

text = text.replace(
"""
            concrete_pad_present,

            bench_feasible,

            curb_access_clear,

            notes
""",
"""
            bench_feasible,

            notes
"""
)

text = text.replace(
"""
        (
            physical_stop_id,
            shelter_present,
            bench_present,
            concrete_pad_present,
            bench_feasible,
            curb_access_clear,
            notes
        ) = review
""",
"""
        (
            physical_stop_id,
            shelter_present,
            bench_present,
            bench_feasible,
            notes
        ) = review
"""
)

text = text.replace(
"if not has_bench and bench_location_feasible:",
"if bench_present == 'no' and bench_feasible == 'yes':"
)

text = text.replace(
"if not has_shelter:",
"if shelter_present == 'no':"
)

text = text.replace(
"""
        if not curb_access_clear:

            recommendations.append(
                "accessibility_improvement"
            )
""",
""
)

p.write_text(text)

print("Fixed update_recommendations_from_reviews for stop_observations")
