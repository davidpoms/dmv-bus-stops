from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''        # Shelter
        "shelter_protection":
            "shelter_type",


'''

if old not in text:
    raise Exception("Shelter mapping block not found")

text = text.replace(old, "")

p.write_text(text)

print("Removed shelter_protection -> shelter_type mapping")
