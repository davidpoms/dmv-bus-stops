from pathlib import Path
import shutil
from datetime import datetime


APP = Path("src/api/app.py")
JS = Path("src/dashboard/static/dashboard.js")


def backup(path):
    backup_path = path.with_suffix(
        path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    shutil.copy(path, backup_path)
    print("Backup created:", backup_path)


def fix_app():
    text = APP.read_text(encoding="utf-8")

    marker = """
(stop_id,)
)


    projects = []
"""

    replacement = """
(stop_id,)
)


    if not stop:
        return {"error": "Stop not found"}, 404


    row = stop[0]


    projects = []
"""

    if marker not in text:
        print("Could not find stop_detail insertion point")
        return

    text = text.replace(marker, replacement, 1)

    APP.write_text(text, encoding="utf-8")

    print("Fixed stop_detail row assignment")


def fix_dashboard_js():

    if not JS.exists():
        print("dashboard.js not found")
        return

    text = JS.read_text(encoding="utf-8")

    old = """
fetch(`/stops/${stopId}/amenities`)
"""

    if old in text:
        text = text.replace(
            old,
            "// removed obsolete amenities endpoint"
        )
        JS.write_text(text, encoding="utf-8")
        print("Removed obsolete amenities fetch")

    else:
        print("No obsolete amenities fetch found")


if __name__ == "__main__":

    backup(APP)
    backup(JS)

    fix_app()
    fix_dashboard_js()

    print("Done.")