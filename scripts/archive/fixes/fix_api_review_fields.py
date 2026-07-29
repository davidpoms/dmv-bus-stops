from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

replacements = {
    'data.get("anonymous_email") or data.get("user_id", "")':
        'data.get("observer", "")',

    'data.get("has_shelter")':
        'data.get("shelter_present")',

    'data.get("has_bench")':
        'data.get("bench_present")',

    'data.get("bench_location_feasible")':
        'data.get("bench_feasible")',

    'has_shelter':
        'shelter_present',

    'has_bench':
        'bench_present',

}

for old, new in replacements.items():
    text = text.replace(old, new)

p.write_text(text)

print("Fixed API review fields")
