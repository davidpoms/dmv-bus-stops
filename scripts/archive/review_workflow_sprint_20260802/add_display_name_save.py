from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")

needle = """
    session["reviewer_key"] = reviewer_key


    if not assignment_id:
"""

replacement = '''
    session["reviewer_key"] = reviewer_key


    display_name = data.get(
        "display_name",
        ""
    ).strip()


    if display_name:

        query_db(
            """
            UPDATE community_reviewers
            SET display_name=?
            WHERE id=?
            """,
            (
                display_name,
                reviewer_id
            )
        )


    if not assignment_id:
'''

if needle not in text:
    raise SystemExit("Could not find submit review insertion point")

text = text.replace(
    needle,
    replacement
)

path.write_text(
    text,
    encoding="utf-8"
)

print("Added display name save logic")