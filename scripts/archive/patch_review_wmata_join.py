from pathlib import Path


file = Path("src/api/app.py")

text=file.read_text()


old="""
LEFT JOIN stop_wmata_evidence w
ON p.id = w.physical_stop_id
"""


new="""
LEFT JOIN active_wmata_evidence w
ON p.id = w.physical_stop_id
"""


if old not in text:
    raise Exception("Join not found")


text=text.replace(old,new,1)


file.write_text(text)

print("Patched review WMATA join")