from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

duplicate = '''
                "availability":
                    "confirmed"
                    if row[9]
                    else "unavailable",

                "availability":
                    "confirmed"
                    if row[9]
                    else "unavailable"
'''

single = '''
                "availability":
                    "confirmed"
                    if row[9]
                    else "unavailable"
'''

if duplicate not in text:
    raise Exception("Duplicate availability block not found")

text = text.replace(duplicate, single, 1)

path.write_text(text)

print("Removed duplicate WMATA availability field")
