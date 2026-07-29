from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
    stop_row = stop[0] if stop else None


    return jsonify(
"""

new = """
    stop_row = stop[0] if stop else None

    evidence = get_stop_evidence_summary(stop_id)


    return jsonify(
"""

if old not in text:
    raise Exception("Injection point not found")

text = text.replace(old, new, 1)


old = """
            "projects": [
                {
                    "recommendation": row[0],
                    "status": row[1]
                }
                for row in projects
            ]
        }
    )
"""

new = """
            "projects": [
                {
                    "recommendation": row[0],
                    "status": row[1]
                }
                for row in projects
            ],

            "evidence": evidence
        }
    )
"""

if old not in text:
    raise Exception("JSON block not found")

text = text.replace(old, new, 1)

p.write_text(text)

print("Added evidence to stop detail API")
