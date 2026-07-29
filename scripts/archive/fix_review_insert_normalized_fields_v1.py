from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

replacements = {
    'data.get("shelter_protection"),':
        'data.get("shelter_type", ""),',

    'data.get("seating_type"),':
        'data.get("bench_type", ""),',

    'data.get("seating_limitations"),':
        'data.get("bench_condition", ""),',

    'data.get("waiting_environment_rating"),':
        'data.get("rider_comfort_category", ""),',

    'data.get("reviewer_relationship", ""),':
        'data.get("observer", ""),',

    'data.get("steward_interest"),':
        'data.get("property_owner_outreach", ""),',
}


changed = 0

for old, new in replacements.items():

    if old in text:
        text = text.replace(old, new)
        changed += 1


if changed == 0:
    raise Exception(
        "No INSERT mappings found to replace"
    )


p.write_text(text)

print(
    f"Updated {changed} INSERT mappings"
)
