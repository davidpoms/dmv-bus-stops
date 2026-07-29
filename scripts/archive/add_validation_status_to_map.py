from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


# Add validation join after stop_improvement_impact join
old = """
            JOIN stop_improvement_impact sii
                ON ps.id = sii.physical_stop_id
"""


new = """
            JOIN stop_improvement_impact sii
                ON ps.id = sii.physical_stop_id

            LEFT JOIN stop_validation sv
                ON ps.id = sv.physical_stop_id
"""


if text.count(old) == 0:
    print("join block not found")
    raise SystemExit(1)


text = text.replace(
    old,
    new
)


# Add validation field to SELECTs
old_select = """
                sii.priority_level
"""


new_select = """
                sii.priority_level,
                COALESCE(
                    sv.status,
                    'needs_validation'
                )
"""


text = text.replace(
    old_select,
    new_select
)


# Add property to JSON output
old_props = """
                        "priority": row[6]
"""


new_props = """
                        "priority": row[6],
                        "validation_status": row[7]
"""


text = text.replace(
    old_props,
    new_props
)


p.write_text(text)

print("validation status added to map endpoint")

