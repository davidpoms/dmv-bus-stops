from pathlib import Path


path = Path("src/api/app.py")

text = path.read_text()


old = """
    data = request.json

    print("DEBUG REVIEW PAYLOAD:")
    print(data)

    stop_id = data.get("stop_id")
"""


new = """
    data = request.json

    print("DEBUG REVIEW PAYLOAD:")
    print(data)


    # Normalize new survey fields into database vocabulary.
    # The survey UI uses human-friendly names while
    # stop_observations uses the original schema names.

    field_map = {

        # Shelter
        "shelter_protection":
            "shelter_type",


        # Seating
        "seating_type":
            "bench_type",

        "seating_limitations":
            "bench_condition",


        # Accessibility
        "accessibility_status":
            "accessibility_status",


        # Comfort
        "waiting_environment_rating":
            "rider_comfort_category",


        # Reviewer identity/context
        "reviewer_relationship":
            "observer",


        # Steward outreach
        "steward_interest":
            "property_owner_outreach",

    }


    for survey_field, db_field in field_map.items():

        if survey_field in data:

            data[db_field] = data[survey_field]


    # Convert yes/no steward interest into boolean flag

    if "steward_interest" in data:

        data["steward_candidate"] = (
            1
            if data["steward_interest"] in
            ("yes", "maybe")
            else 0
        )


    stop_id = data.get("stop_id")
"""


if old not in text:
    raise Exception(
        "Could not find submit_review payload block"
    )


text = text.replace(
    old,
    new
)


path.write_text(text)

print(
    "Added review field mapping"
)
