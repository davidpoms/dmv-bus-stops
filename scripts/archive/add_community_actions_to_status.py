from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = '''
    projects = query_db(
        """
        SELECT
            recommendation_type,
            project_status,
            assigned_team,
            completed_date
        FROM improvement_projects
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )
'''


new = '''
    projects = query_db(
        """
        SELECT
            recommendation_type,
            project_status,
            assigned_team,
            completed_date
        FROM improvement_projects
        WHERE physical_stop_id = ?
        """,
        (stop_id,)
    )


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
'''


if old not in text:
    print("project query block not found")
    raise SystemExit(1)


text = text.replace(old, new)


old2 = '''
            "community_project": {
                "improvements": installed_projects
            }
'''


new2 = '''
            "community_project": {
                "improvements": installed_projects
            },

            "community_action": [
                {
                    "status": row[0],
                    "type": row[1],
                    "steward": row[2],
                    "installed_date": row[3],
                    "notes": row[4]
                }
                for row in community_actions
            ]
'''


if old2 not in text:
    print("response block not found")
    raise SystemExit(1)


text = text.replace(old2, new2)


p.write_text(text)

print("community actions added to status endpoint")
