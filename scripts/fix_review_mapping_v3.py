from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

start = text.find(
    "# Normalize survey fields into database fields"
)

if start == -1:
    raise Exception(
        "Could not find normalization section"
    )

end = text.find(
    "# Convert yes/no steward interest",
    start
)

if end == -1:
    raise Exception(
        "Could not find end of normalization section"
    )


new_block = '''# Normalize survey fields into database fields

    data["shelter_type"] = (
        data.get("shelter_protection", "")
    )

    data["bench_type"] = (
        data.get("seating_type", "")
    )

    data["bench_condition"] = (
        data.get("seating_limitations", "")
    )

    data["rider_comfort_category"] = (
        data.get("waiting_environment_rating", "")
    )

    data["observer"] = (
        data.get("reviewer_relationship", "")
    )

    data["property_owner_outreach"] = (
        data.get("steward_interest", "")
    )

    data["review_mode"] = (
        data.get("review_mode", "")
    )

    data["rider_activity"] = (
        data.get("rider_activity", "")
    )

    data["usage_times"] = (
        data.get("usage_times", "")
    )

    '''


text = (
    text[:start]
    + new_block
    + text[end:]
)


p.write_text(text)

print(
    "Fixed review field normalization mapping"
)
