from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

needle = """
    if validation:
"""

insert = '''
    community_actions = query_db(
        """
        SELECT
            status,
            project_type,
            steward,
            installed_date,
            notes
        FROM community_actions
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )


    if validation:
'''


if needle not in text:
    print("validation block not found")
    raise SystemExit(1)


text = text.replace(
    needle,
    insert,
    1
)


p.write_text(text)

print("community actions query added")
