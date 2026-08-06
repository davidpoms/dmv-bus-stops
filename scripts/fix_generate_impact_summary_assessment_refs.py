from pathlib import Path


FILE = Path(
    "src/assessment/generate_impact_summary.py"
)


text = FILE.read_text()


replacements = {
    "assessment.get(": "factors.get(",
    "assessment\n                .get(": "factors\n                .get(",
    "assessment\n            .get(": "factors\n            .get(",
    "assessment\n        .get(": "factors\n        .get(",
}


changed = False


for old, new in replacements.items():

    if old in text:
        text = text.replace(old, new)
        changed = True


if not changed:
    raise Exception(
        "No assessment references found to replace"
    )


FILE.write_text(text)


print(
    "Fixed remaining assessment references"
)