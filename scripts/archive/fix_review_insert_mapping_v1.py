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
            data.get("reviewer_relationship", ""),
            data.get("shelter_present"),
            data.get("shelter_type"),
            data.get("seating_type"),
            data.get("seating_limitations"),
            data.get("bench_feasible"),
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

if old not in text:
    raise Exception("Old INSERT tuple not found")

text = text.replace(old, new)

p.write_text(text)

print("Updated review insert mapping")
