from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = """
    projects = query_db(
        \"\"\"
        SELECT
            recommendation_type,
            project_status

        FROM improvement_projects

        WHERE physical_stop_id = ?;
        \"\"\",
        (stop_id,)
    )
"""

new = """
    projects = []
"""

if old not in text:
    raise Exception("Could not find improvement_projects block")

text = text.replace(old, new)

path.write_text(text)

print("Removed old improvement_projects dependency.")