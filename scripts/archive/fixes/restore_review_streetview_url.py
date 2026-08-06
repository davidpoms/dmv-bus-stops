from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''
            "municipality": row[8],

            "wmata_evidence": {
'''

new = '''
            "municipality": row[8],

            "streetview_url": streetview_url,

            "wmata_evidence": {
'''

if old not in text:
    raise Exception(
        "Could not find review info response block"
    )

text = text.replace(old,new,1)

p.write_text(text)

print("Restored streetview_url in review info endpoint")
