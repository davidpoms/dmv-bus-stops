from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''                "priority": row[5],
                "status": row[6]
'''

new = '''                "priority": row[5],
                "status": row[6],
                "streetview_url":
                    f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={row[2]},{row[3]}"
'''

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text)
    print("Added Street View links")
else:
    print("Pattern not found")
