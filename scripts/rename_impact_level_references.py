from pathlib import Path

files = [
    Path("src/reporting/stop_detail.py"),
    Path("src/reporting/generate_implementation_summary.py"),
    Path("src/reporting/export_improvement_report.py"),
    Path("src/reporting/export_priority_report.py"),
    Path("src/api/app.py"),
    Path("src/assessment/create_project_priorities.py"),
]

for path in files:
    if not path.exists():
        print(f"Missing: {path}")
        continue

    text = path.read_text()
    original = text

    text = text.replace(
        "impact_level",
        "priority_level"
    )

    if text != original:
        path.write_text(text)
        print(f"Updated {path}")
    else:
        print(f"No changes: {path}")
