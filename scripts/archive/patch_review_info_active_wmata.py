from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


old = """
        LEFT JOIN stop_wmata_evidence w
        ON p.id=w.physical_stop_id
"""


new = """
        LEFT JOIN active_wmata_evidence w
        ON p.id=w.physical_stop_id
"""


if old not in text:
    raise Exception("Review WMATA join not found")


text = text.replace(old, new, 1)


path.write_text(text)

print("Patched review_stop_info to use active_wmata_evidence")