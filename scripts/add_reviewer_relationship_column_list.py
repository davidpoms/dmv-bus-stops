from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
            source,
            review_mode,
            rider_activity,
            usage_times,
"""

new = """
            source,
            review_mode,
            reviewer_relationship,
            rider_activity,
            usage_times,
"""

if old not in text:
    raise Exception("Could not find INSERT column list")

text = text.replace(old, new, 1)

p.write_text(text)

print("Added reviewer_relationship to INSERT columns")
