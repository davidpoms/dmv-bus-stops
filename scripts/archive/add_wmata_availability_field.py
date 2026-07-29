from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = '"match_confidence": row[16]'

new = '''"match_confidence": row[16],
                "availability":
                    "confirmed"
                    if row[9]
                    else "unavailable"'''

if old not in text:
    raise Exception("Could not find match_confidence line")

if '"availability":' in text:
    print("Availability field already exists")
else:
    text = text.replace(old, new, 1)
    path.write_text(text)
    print("Added WMATA availability field")
