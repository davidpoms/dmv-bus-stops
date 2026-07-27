from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = """
    stop_id = data.get("stop_id")
    reviewer_id = data.get("reviewer_id")
    assignment_id = data.get("assignment_id")
"""


new = """
    # Normalize survey fields into database fields

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

    data["steward_candidate"] = (
        1
        if data.get("steward_interest")
        in ("yes", "maybe")
        else 0
    )


    stop_id = data.get("stop_id")
    reviewer_id = data.get("reviewer_id")
    assignment_id = data.get("assignment_id")
"""


if old not in text:
    raise Exception(
        "Could not find normalization insertion point"
    )


text = text.replace(old, new)

p.write_text(text)

print("Fixed payload normalization")
