from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
        INSERT INTO stop_observations
        (
            physical_stop_id,
            observer,
            shelter_present,
            bench_present,
            notes,
            reviewer_id
        )
        VALUES (?, ?, ?, ?, ?, ?)
"""

new = """
        INSERT INTO stop_observations
        (
            physical_stop_id,
            observer,
            shelter_present,
            bench_present,
            bench_type,
            bench_back,
            bench_hostile_features,
            rider_comfort_category,
            shelter_type,
            accessibility_status,
            notes,
            reviewer_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

if old not in text:
    print("Could not find original INSERT block")
    print("Search submit_review manually")
    exit()

text = text.replace(old, new)

old_values = """
            (
                data["stop_id"],
                data.get("observer"),
                data.get("shelter_present"),
                data.get("bench_present"),
                data.get("notes"),
                data.get("reviewer_id")
            )
"""

new_values = """
            (
                data["stop_id"],
                data.get("observer"),
                data.get("shelter_present"),
                data.get("bench_present"),
                data.get("bench_type"),
                data.get("bench_back"),
                data.get("bench_hostile_features"),
                data.get("rider_comfort_category"),
                data.get("shelter_type"),
                data.get("accessibility_status"),
                data.get("notes"),
                data.get("reviewer_id")
            )
"""

if old_values not in text:
    print("Could not find INSERT values block")
    exit()

text = text.replace(old_values, new_values)

p.write_text(text)

print("Review submission fields updated")
