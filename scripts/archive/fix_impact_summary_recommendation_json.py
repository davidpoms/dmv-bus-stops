from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


old = """                    "recommendations":
                        impact_summary[0][2].split(",")
                        if impact_summary[0][2]
                        else [],
"""


new = """                    "recommendations":
                        json.loads(impact_summary[0][2])
                        if impact_summary[0][2]
                        else [],
"""


if old not in text:
    raise Exception("Could not find impact recommendations block")


text = text.replace(old, new, 1)

path.write_text(text)

print("Fixed impact summary recommendation JSON parsing")