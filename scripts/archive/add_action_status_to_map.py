from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = """
                COALESCE(
                    sv.status,
                    'needs_validation'
                )

            FROM physical_stops ps
"""


new = """
                COALESCE(
                    sv.status,
                    'needs_validation'
                ),

                COALESCE(
                    ca.status,
                    'none'
                )

            FROM physical_stops ps
"""


if text.count(old) == 0:
    print("map select block not found")
    raise SystemExit(1)


text = text.replace(
    old,
    new
)


old_join = """
            LEFT JOIN stop_validation sv
                ON ps.id = sv.physical_stop_id
"""


new_join = """
            LEFT JOIN stop_validation sv
                ON ps.id = sv.physical_stop_id

            LEFT JOIN community_actions ca
                ON ps.id = ca.physical_stop_id
"""


if text.count(old_join) == 0:
    print("validation join not found")
    raise SystemExit(1)


text = text.replace(
    old_join,
    new_join
)


old_property = """
                        "validation_status": row[7]
"""


new_property = """
                        "validation_status": row[7],
                        "action_status": row[8]
"""


if text.count(old_property) == 0:
    print("map property block not found")
    raise SystemExit(1)


text = text.replace(
    old_property,
    new_property
)


p.write_text(text)

print("action status added to map")
