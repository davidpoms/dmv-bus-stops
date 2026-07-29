from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
                dc_ward,
                dc_ward,
                action_filter,
                action_filter,
                review_mode,
                review_mode,
                review_mode
"""

new = """
                dc_ward,
                dc_ward,
                review_mode,
                review_mode,
                review_mode,
                action_filter,
                action_filter
"""

count = text.count(old)

if count == 0:
    print("binding order blocks not found")
    raise SystemExit(1)

text = text.replace(old, new)

p.write_text(text)

print(f"fixed {count} binding blocks")
