from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''    data["shelter_type"] = data.get(
        "shelter_type",
        ""
    )
'''

new = '''    data["shelter_type"] = (
        data.get("shelter_type")
        or data.get("shelter_protection")
        or ""
    )
'''

if old not in text:
    raise Exception("Could not find shelter_type normalization block")

text = text.replace(old, new, 1)

p.write_text(text)

print("Fixed shelter_type normalization")
