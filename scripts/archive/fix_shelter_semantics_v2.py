from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''    data["shelter_type"] = data.get(
        "shelter_protection",
        data.get("shelter_type", "")
    )
'''

new = '''    data["shelter_type"] = data.get(
        "shelter_type",
        ""
    )

    data["shelter_protection"] = data.get(
        "shelter_protection",
        ""
    )
'''

if old not in text:
    raise Exception("Old shelter normalization block not found")

text = text.replace(old, new)

p.write_text(text)

print("Fixed shelter semantic normalization")
