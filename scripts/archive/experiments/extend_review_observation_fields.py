from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old_columns = """
            bench_feasible,
            ada_clearance_possible,
            notes,
            reviewer_id,
            confidence,
            source
"""

new_columns = """
            bench_feasible,
            ada_clearance_possible,
            bench_type,
            bench_condition,
            bench_back,
            bench_hostile_features,
            shelter_type,
            rider_comfort_category,
            accessibility_status,
            notes,
            reviewer_id,
            confidence,
            source
"""


if old_columns not in text:
    raise Exception("Could not find INSERT column block")


text = text.replace(
    old_columns,
    new_columns,
    1
)


old_values = """
        (?, ?, ?, ?, ?, ?, ?, ?, ?, 'community_review')
"""

new_values = """
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'community_review')
"""


if old_values not in text:
    raise Exception("Could not find INSERT values block")


text = text.replace(
    old_values,
    new_values,
    1
)


old_data = """
            data.get("bench_feasible"),
            data.get("ada_clearance_possible"),
            data.get("notes"),
            data.get("reviewer_id"),
            data.get("reviewer_confidence")
"""


new_data = """
            data.get("bench_feasible"),
            data.get("ada_clearance_possible"),
            data.get("bench_type"),
            data.get("bench_condition"),
            data.get("bench_back"),
            data.get("bench_hostile_features"),
            data.get("shelter_type"),
            data.get("rider_comfort_category"),
            data.get("accessibility_status"),
            data.get("notes"),
            data.get("reviewer_id"),
            data.get("reviewer_confidence")
"""


if old_data not in text:
    raise Exception("Could not find INSERT parameter block")


text = text.replace(
    old_data,
    new_data,
    1
)


p.write_text(text)

print("Extended review observation fields")
