from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

replacements = [
(
'''    data["shelter_type"] = data.get(
        "shelter_type",
        ""
    )

    data["shelter_protection"] = data.get(
        "shelter_protection",
        ""
    )
''',
'''    data["shelter_type"] = (
        data.get("shelter_type")
        or data.get("shelter_protection")
        or ""
    )
'''
),
(
'''    data["bench_type"] = data.get(
        "seating_type",
        data.get("bench_type", "")
    )
''',
'''    data["bench_type"] = (
        data.get("bench_type")
        or data.get("seating_type")
        or ""
    )
'''
),
(
'''    data["bench_condition"] = data.get(
        "seating_limitations",
        data.get("bench_condition", "")
    )
''',
'''    data["bench_condition"] = (
        data.get("bench_condition")
        or data.get("seating_limitations")
        or ""
    )
'''
),
(
'''    data["rider_comfort_category"] = data.get(
        "waiting_environment_rating",
        data.get("rider_comfort_category", "")
    )
''',
'''    data["rider_comfort_category"] = (
        data.get("rider_comfort_category")
        or data.get("waiting_environment_rating")
        or ""
    )
'''
)
]

for old, new in replacements:
    if old in text:
        text = text.replace(old, new, 1)
        print("Replaced block")
    else:
        print("Skipped missing block")

p.write_text(text)

print("Done")
