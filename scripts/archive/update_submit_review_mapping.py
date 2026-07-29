from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = '''        (
            data.get("stop_id"),
            data.get("observer", ""),
            data.get("shelter_present"),
            data.get("bench_present"),
            data.get("bench_feasible"),
            data.get("ada_clearance_possible"),
            data.get("bench_type"),
            data.get("bench_condition"),
            data.get("bench_back"),
            data.get("bench_hostile_features"),
            data.get("shelter_type"),
            data.get("rider_comfort_category"),
            data.get("accessibility_status"),
            data.get("notes"),
            data.get("reviewer_id"),
            data.get("reviewer_confidence"),
            "community_review",
            data.get("review_mode"),
            data.get("rider_activity"),
            data.get("usage_times"),
            data.get("property_owner_outreach"),
            data.get("steward_email"),
            data.get("steward_candidate", 0),
            data.get("concrete_pad_needed")
        )
'''


new = '''        (
            data.get("stop_id"),

            # observer
            data.get("reviewer_relationship", ""),

            # shelter
            data.get("shelter_present"),

            # bench/seating
            "yes" if data.get("seating_type") else data.get("bench_present"),
            data.get("bench_feasible"),

            # accessibility
            data.get("accessibility_status"),

            # notes
            data.get("notes"),

            # reviewer
            data.get("reviewer_id"),

            # confidence fallback
            data.get("reviewer_confidence", "unknown"),

            # source
            "community_review",

            # mode
            data.get("review_mode"),

            # activity
            data.get("rider_activity"),

            # usage
            data.get("usage_times"),

            # stewardship
            data.get("steward_interest") in ("yes", "maybe"),

            data.get("steward_email"),

            # bench details
            data.get("seating_type"),
            data.get("seating_limitations"),

            # shelter details
            data.get("shelter_protection"),

            # hostile design
            data.get("riders_avoid_facilities"),

            # rider comfort
            data.get("waiting_environment_rating"),

            # back/features
            data.get("bench_back"),
            data.get("bench_hostile_features"),

            # property outreach
            data.get("steward_interest"),

            # pad
            data.get("concrete_pad_needed")
        )
'''


if old not in text:
    raise SystemExit(
        "Could not find old payload mapping block"
    )


text = text.replace(old, new)

p.write_text(text)

print("Updated submit_review mapping")
