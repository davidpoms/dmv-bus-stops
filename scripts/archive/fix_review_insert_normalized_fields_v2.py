from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

replacements = {
    'data.get("seating_type")':
        'data.get("bench_type", "")',

    'data.get("seating_limitations")':
        'data.get("bench_condition", "")',

    'data.get("waiting_environment_rating")':
        'data.get("rider_comfort_category", "")',

    'data.get("reviewer_relationship")':
        'data.get("observer", "")',

    'data.get("steward_interest")':
        'data.get("property_owner_outreach", "")',
}


changed = 0

for old, new in replacements.items():

    count = text.count(old)

    if count:
        text = text.replace(old, new)
        changed += count


if changed == 0:
    raise Exception(
        "No raw survey fields found"
    )


p.write_text(text)

print(
    f"Replaced {changed} raw survey field references"
)
