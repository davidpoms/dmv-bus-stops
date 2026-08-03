from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")

needle = """
    return render_template(
        "review.html",
        stop=stop_row,
        stop_id=stop_id,
        survey_html=render_survey()
    )
"""

replacement = '''
    reviewer_key = session.get("reviewer_key")

    reviewer = None

    if reviewer_key:
        reviewer = query_db(
            """
            SELECT
                display_name
            FROM community_reviewers
            WHERE reviewer_key=?
            """,
            (reviewer_key,)
        )


    reviewer_name = (
        reviewer[0][0]
        if reviewer and reviewer[0][0]
        else None
    )


    return render_template(
        "review.html",
        stop=stop_row,
        stop_id=stop_id,
        survey_html=render_survey(),
        reviewer_name=reviewer_name
    )
'''

if needle not in text:
    raise SystemExit("review template insertion point not found")

text = text.replace(
    needle,
    replacement
)

path.write_text(
    text,
    encoding="utf-8"
)

print("Added reviewer identity to review page")