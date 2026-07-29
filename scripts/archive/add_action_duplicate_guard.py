from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

needle = '''
    notes = data.get(
        "notes"
    )


    query_db(
'''

replacement = '''
    notes = data.get(
        "notes"
    )


    existing_action = query_db(
        """
        SELECT
            id,
            status
        FROM community_actions
        WHERE physical_stop_id = ?
        AND status IN (
            'planned',
            'in_progress',
            'installed'
        )
        ORDER BY id DESC
        LIMIT 1
        """,
        (stop_id,)
    )


    if existing_action:

        return jsonify(
            {
                "status": "already_exists",
                "stop_id": stop_id,
                "existing_status":
                    existing_action[0][1]
            }
        )


    query_db(
'''

if needle not in text:
    print("insert point not found")
    raise SystemExit(1)

text = text.replace(
    needle,
    replacement,
    1
)

p.write_text(text)

print("duplicate action guard added")
