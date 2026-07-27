from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

replacements = {
'''    data["shelter_type"] = data.get(
        "shelter_protection"
    )''':
'''    data["shelter_type"] = (
        data.get("shelter_protection", "")
    )''',

'''    data["bench_type"] = data.get(
        "seating_type"
    )''':
'''    data["bench_type"] = (
        data.get("seating_type", "")
    )''',

'''    data["bench_condition"] = data.get(
        "seating_limitations"
    )''':
'''    data["bench_condition"] = (
        data.get("seating_limitations", "")
    )''',

'''    data["rider_comfort_category"] = data.get(
        "waiting_environment_rating"
    )''':
'''    data["rider_comfort_category"] = (
        data.get("waiting_environment_rating", "")
    )''',

'''    data["observer"] = data.get(
        "reviewer_relationship"
    )''':
'''    data["observer"] = (
        data.get("reviewer_relationship", "")
    )''',

'''    data["property_owner_outreach"] = data.get(
        "steward_interest"
    )''':
'''    data["property_owner_outreach"] = (
        data.get("steward_interest", "")
    )''',
}

changed = 0

for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)
        changed += 1

if changed == 0:
    raise Exception(
        "No mappings found to replace. Run sed -n '780,850p' src/api/app.py"
    )

p.write_text(text)

print(
    f"Updated {changed} review mappings"
)
