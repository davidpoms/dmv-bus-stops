from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''    # Normalize survey fields into database fields

    data["shelter_type"] = data.get(
        "shelter_protection"
    )

    data["bench_type"] = data.get(
        "seating_type"
    )

    data["bench_condition"] = data.get(
        "seating_limitations"
    )

    data["rider_comfort_category"] = data.get(
        "waiting_environment_rating"
    )

    data["observer"] = data.get(
        "reviewer_relationship"
    )

    data["property_owner_outreach"] = data.get(
        "steward_interest"
    )

'''

new = '''    # Normalize survey fields into database fields

    data["shelter_type"] = (
        data.get("shelter_protection")
        or ""
    )

    data["bench_type"] = (
        data.get("seating_type")
        or ""
    )

    data["bench_condition"] = (
        data.get("seating_limitations")
        or ""
    )

    data["rider_comfort_category"] = (
        data.get("waiting_environment_rating")
        or ""
    )

    data["observer"] = (
        data.get("reviewer_relationship")
        or ""
    )

    data["property_owner_outreach"] = (
        data.get("steward_interest")
        or ""
    )

'''

if old not in text:
    raise Exception(
        "Normalization block not found"
    )

text = text.replace(old,new)

p.write_text(text)

print("Updated normalization mapping")
