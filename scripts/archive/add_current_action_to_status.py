from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

needle = """
    field_review_status = (
        "completed"
        if validation_status == "validated"
        else
        "not_started"
    )


    return jsonify(
"""

replacement = """
    field_review_status = (
        "completed"
        if validation_status == "validated"
        else
        "not_started"
    )


    current_action = (
        community_actions[0]
        if community_actions
        else None
    )


    return jsonify(
"""

if needle not in text:
    print("insert location not found")
    raise SystemExit(1)

text = text.replace(
    needle,
    replacement,
    1
)


needle2 = """
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

"""

replacement2 = """
                "community_action": [

                    {
                        "status": row[0],
                        "type": row[1],
                        "steward": row[2],
                        "installed_date": row[3],
                        "notes": row[4]
                    }

                    for row in community_actions
                ],


                "current_action":
                    {
                        "status": current_action[0],
                        "type": current_action[1],
                        "steward": current_action[2],
                        "installed_date": current_action[3],
                        "notes": current_action[4]
                    }
                    if current_action
                    else None

"""

if needle2 not in text:
    print("community action block not found")
    raise SystemExit(1)

text = text.replace(
    needle2,
    replacement2,
    1
)

p.write_text(text)

print("current action added")
