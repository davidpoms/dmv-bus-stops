from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

replacements = {
    'summary["total"]': 'summary[0] if isinstance(summary, tuple) else summary.get("total", 0)',
    'summary["likely_shelter"]': 'summary[1] if isinstance(summary, tuple) else summary.get("likely_shelter", 0)',
    'summary["likely_bench"]': 'summary[2] if isinstance(summary, tuple) else summary.get("likely_bench", 0)',
    'summary["no_shelter_evidence"]': 'summary[3] if isinstance(summary, tuple) else summary.get("no_shelter_evidence", 0)',
}

for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)
        print("Fixed:", old)
    else:
        print("Not found:", old)

path.write_text(text)

print("Evidence summary route patched")
