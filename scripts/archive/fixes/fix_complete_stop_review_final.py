from pathlib import Path

p = Path("src/review/complete_stop_review.py")

text = p.read_text()

text = text.replace(
"""
        WHERE stop_id = ?
        AND reviewer_id = ?;
""",
"""
        WHERE physical_stop_id = ?
        AND reviewer_id = ?;
"""
)

text = text.replace(
"""
        f"Saved review for stop {stop_id}"
""",
"""
        f"Saved review for stop {physical_stop_id}"
"""
)

text = text.replace(
"""
    complete_stop_review(
        stop_id=5478,
        reviewer_id="demo_volunteer",
        has_shelter=False,
        has_bench=False,
        bench_condition="none",
        waiting_area_type="sidewalk",
        notes="High ridership stop with no existing seating."
    )
""",
"""
    complete_stop_review(
        physical_stop_id=5478,
        reviewer_id="demo_volunteer",
        shelter_present="no",
        bench_present="no",
        bench_condition="none",
        waiting_area_type="sidewalk",
        notes="High ridership stop with no existing seating."
    )
"""
)

p.write_text(text)

print("Fixed complete_stop_review")
