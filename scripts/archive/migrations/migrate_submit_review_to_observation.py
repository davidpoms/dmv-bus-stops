from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
        INSERT INTO stop_reviews
        (
            stop_id,
            user_id,
            anonymous_email,
            waiting_area_type,
            concrete_pad_present,
            bench_location_feasible,
            sun_exposure,
            reviewer_confidence,
            notes
        )

        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

new = """
        INSERT INTO stop_observations
        (
            physical_stop_id,
            observer,
            shelter_present,
            bench_present,
            bench_feasible,
            ada_clearance_possible,
            notes,
            reviewer_id,
            confidence,
            source
        )

        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, 'community_review')
"""

if old not in text:
    print("INSERT block not found")
    raise SystemExit(1)

text = text.replace(old, new)

old_values = """
            data.get("stop_id"),
            data.get("user_id"),
            data.get("anonymous_email"),
            data.get("waiting_area_type"),
            data.get("concrete_pad_present"),
            data.get("bench_location_feasible"),
            data.get("sun_exposure"),
            data.get("reviewer_confidence"),
            data.get("notes")
"""

new_values = """
            data.get("stop_id"),
            data.get("anonymous_email") or data.get("user_id", ""),
            data.get("has_shelter"),
            data.get("has_bench"),
            data.get("bench_location_feasible"),
            data.get("ada_clearance_possible"),
            data.get("notes"),
            data.get("reviewer_id"),
            data.get("reviewer_confidence")
"""

if old_values not in text:
    print("VALUES block not found")
    raise SystemExit(1)

text = text.replace(old_values, new_values)

p.write_text(text)

print("Migrated review submission endpoint to stop_observations")
