from pathlib import Path


path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = '''        "wmata_evidence": wmata_evidence
'''


new = '''        "wmata_evidence": wmata_evidence,

        "ddot_shelter_evidence":
            evidence.get("ddot", [])
'''


if new in text:
    print("Already patched")
elif old in text:
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("Added DDOT shelter evidence to stop API")
else:
    raise Exception(
        "Could not find wmata_evidence return block"
    )