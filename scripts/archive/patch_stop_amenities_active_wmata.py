from pathlib import Path


file = Path("src/api/app.py")

text = file.read_text()


old = """
FROM stop_wmata_evidence
WHERE physical_stop_id = ?
"""


new = """
FROM active_wmata_evidence
WHERE physical_stop_id = ?
"""


if old not in text:
    raise Exception("Could not find query")


text = text.replace(old,new,1)


file.write_text(text)

print("Patched amenities endpoint")