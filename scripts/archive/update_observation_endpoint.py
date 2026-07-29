from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = """            shelter_present,
            bench_present,
            trash_present,
            bench_feasible,
            ada_clearance_possible,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

new = """            shelter_present,
            bench_present,
            trash_present,
            bench_feasible,
            ada_clearance_possible,
            review_mode,
            rider_activity,
            usage_times,
            property_owner_outreach,
            steward_email,
            steward_candidate,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


if old not in text:
    raise SystemExit(
        "Could not find observation INSERT fields."
    )


text = text.replace(old, new, 1)


old_values = """            data.get("shelter_present"),
            data.get("bench_present"),
            data.get("trash_present"),
            data.get("bench_feasible"),
            data.get("ada_clearance_possible"),
            data.get("notes", "")
"""


new_values = """            data.get("shelter_present"),
            data.get("bench_present"),
            data.get("trash_present"),
            data.get("bench_feasible"),
            data.get("ada_clearance_possible"),
            data.get("review_mode"),
            data.get("rider_activity"),
            data.get("usage_times"),
            data.get("property_owner_outreach"),
            data.get("steward_email"),
            data.get("steward_candidate", 0),
            data.get("notes", "")
"""


if old_values not in text:
    raise SystemExit(
        "Could not find observation INSERT values."
    )


text = text.replace(old_values, new_values, 1)


path.write_text(text)

print("Updated /observations/create endpoint.")
