from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

replacements = {
'''    data["observer"] = (
        data.get("reviewer_relationship")
        or ""
    )
''':
'''    # Keep observer separate from reviewer relationship
    data["observer"] = data.get("observer", "")
''',

'''    data["shelter_type"] = (
        data.get("shelter_type")
        or ""
    )
''':
'''    # shelter_type is a database field; preserve existing mapping
    data["shelter_type"] = data.get("shelter_type", "")
''',

'''    data["bench_type"] = (
        data.get("seating_type")
        or ""
    )
''':
'''    data["bench_type"] = data.get(
        "bench_type",
        data.get("seating_type", "")
    )
''',

'''    data["bench_condition"] = (
        data.get("seating_limitations")
        or ""
    )
''':
'''    data["bench_condition"] = data.get(
        "bench_condition",
        data.get("seating_limitations", "")
    )
''',

'''    data["rider_comfort_category"] = (
        data.get("waiting_environment_rating")
        or ""
    )
''':
'''    data["rider_comfort_category"] = data.get(
        "rider_comfort_category",
        data.get("waiting_environment_rating", "")
    )
''',

'''    data["property_owner_outreach"] = (
        data.get("steward_interest")
        or ""
    )
''':
'''    data["property_owner_outreach"] = data.get(
        "property_owner_outreach",
        data.get("steward_interest", "")
    )
'''
}

changed = 0

for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new, 1)
        changed += 1

if changed == 0:
    raise Exception("No normalization blocks found")

p.write_text(text)

print(f"Fixed {changed} normalization overwrites")
