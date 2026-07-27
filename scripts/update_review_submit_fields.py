from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old_columns = """
            reviewer_id,
            confidence,
            source
"""

new_columns = """
            reviewer_id,
            confidence,
            source,
            review_mode,
            rider_activity,
            usage_times,
            property_owner_outreach,
            steward_email,
            steward_candidate
"""

if old_columns not in text:
    raise SystemExit(
        "Could not find expected INSERT column section"
    )

text = text.replace(
    old_columns,
    new_columns,
    1
)


old_values = """
            data.get("reviewer_id"),
            data.get("reviewer_confidence"),
            "community_review"
"""

new_values = """
            data.get("reviewer_id"),
            data.get("reviewer_confidence"),
            "community_review",
            data.get("review_mode"),
            data.get("rider_activity"),
            data.get("usage_times"),
            data.get("property_owner_outreach"),
            data.get("steward_email"),
            data.get("steward_candidate", 0)
"""

if old_values not in text:
    raise SystemExit(
        "Could not find expected INSERT values section"
    )

text = text.replace(
    old_values,
    new_values,
    1
)


old_placeholder = """
        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

new_placeholder = """
        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

if old_placeholder not in text:
    raise SystemExit(
        "Could not find expected placeholder section"
    )

text = text.replace(
    old_placeholder,
    new_placeholder,
    1
)


path.write_text(text)

print(
    "Updated /review/submit with new survey fields"
)
