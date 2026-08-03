from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = """
    if display_name:

        query_db(
            \"\"\"
            UPDATE community_reviewers
            SET display_name=?
            WHERE id=?
            \"\"\",
            (
                display_name,
                reviewer_id
            )
        )
"""


new = """
    if display_name:

        query_db(
            \"\"\"
            UPDATE community_reviewers
            SET
                display_name=?,
                profile_created_at=CURRENT_TIMESTAMP
            WHERE id=?
            \"\"\",
            (
                display_name,
                reviewer_id
            )
        )

"""



if old not in text:
    raise SystemExit(
        "Display name update block not found"
    )


text = text.replace(
    old,
    new
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Fixed reviewer display name save"
)