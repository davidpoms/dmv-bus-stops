from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''    print("DEBUG REVIEW PAYLOAD:")
    print(data)
'''

new = '''    print(
        "INSERT DEBUG:",
        {
            "review_mode": data.get("review_mode"),
            "reviewer_relationship": data.get("reviewer_relationship"),
            "shelter_present": data.get("shelter_present"),
            "seating_type": data.get("seating_type"),
            "bench_type": data.get("bench_type"),
            "waiting_environment_rating": data.get("waiting_environment_rating"),
            "rider_comfort_category": data.get("rider_comfort_category"),
        }
    )
'''

if old not in text:
    raise Exception("Debug block not found")

p.write_text(text.replace(old, new))

print("Updated review debug")
