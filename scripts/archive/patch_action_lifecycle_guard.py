from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''
    if existing_action:

        return jsonify(
            {
                "status": "already_exists",
                "stop_id": stop_id,
                "existing_status":
                    existing_action[0][1]
            }
        )


'''

new = '''
    if existing_action:

        existing_id = existing_action[0][0]
        existing_status = existing_action[0][1]

        lifecycle = {
            "planned": 1,
            "in_progress": 2,
            "installed": 3
        }


        if (
            status in lifecycle
            and existing_status in lifecycle
            and lifecycle[status] > lifecycle[existing_status]
        ):

            query_db(
                """
                UPDATE community_actions
                SET
                    status = ?,
                    project_type = ?,
                    steward = ?,
                    installed_date =
                        CASE
                            WHEN ? = 'installed'
                            THEN CURRENT_TIMESTAMP
                            ELSE installed_date
                        END,
                    notes = ?
                WHERE id = ?
                """,
                (
                    status,
                    project_type,
                    steward,
                    status,
                    notes,
                    existing_id
                )
            )


            return jsonify(
                {
                    "status": "updated",
                    "stop_id": stop_id,
                    "previous_status":
                        existing_status,
                    "new_status":
                        status
                }
            )


        return jsonify(
            {
                "status": "already_exists",
                "stop_id": stop_id,
                "existing_status":
                    existing_status
            }
        )


'''

if old not in text:
    print("lifecycle block not found")
    raise SystemExit(1)

text = text.replace(old, new, 1)

p.write_text(text)

print("action lifecycle guard patched")
