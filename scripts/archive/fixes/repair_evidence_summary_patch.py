from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

bad = {
    'summary[0] if isinstance(summary, tuple) else summary.get("total", 0) += row[1]':
        'summary["total"] += row[1]',
    'summary[1] if isinstance(summary, tuple) else summary.get("likely_shelter", 0) += row[2]':
        'summary["likely_shelter"] += row[2]',
    'summary[2] if isinstance(summary, tuple) else summary.get("likely_bench", 0) += row[3]':
        'summary["likely_bench"] += row[3]',
    'summary[3] if isinstance(summary, tuple) else summary.get("no_shelter_evidence", 0) += row[4]':
        'summary["no_shelter_evidence"] += row[4]',
}

for old, new in bad.items():
    if old in text:
        text = text.replace(old, new)
        print("Restored:", old)
    else:
        print("Not found:", old)

path.write_text(text)

print("Repair complete")
