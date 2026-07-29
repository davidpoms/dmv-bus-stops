from pathlib import Path

p = Path("src/review/submit_stop_review.py")

text = p.read_text()

replacements = {
    'data.get("has_shelter")': 'data.get("shelter_present")',
    'data.get("has_bench")': 'data.get("bench_present")',
    'data.get("bench_location_feasible")': 'data.get("bench_feasible")',
    'data.get("reviewer_confidence")': 'data.get("confidence")',
}

for old, new in replacements.items():
    text = text.replace(old, new)

p.write_text(text)

print("Fixed submit_stop_review fields")
