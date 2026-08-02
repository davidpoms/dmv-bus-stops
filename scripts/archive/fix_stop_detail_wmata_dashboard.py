from pathlib import Path
import shutil
from datetime import datetime


APP = Path("src/api/app.py")
JS = Path("src/dashboard/static/dashboard.js")


def backup(path):
    if path.exists():
        backup = path.with_suffix(
            path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        shutil.copy(path, backup)
        print("Backup:", backup)


def fix_wmata():

    text = APP.read_text(encoding="utf-8")

    old = """
"status": wmata_evidence[0][0],
"""

    new = """
"status": wmata_evidence.get("wmata_status"),
"""

    if old in text:
        text = text.replace(old, new)

    old2 = """
"bench": wmata_evidence[0][1],
"""

    new2 = """
"bench": wmata_evidence.get("wmata_bench"),
"""

    text = text.replace(old2, new2)


    old3 = """
"shelter": wmata_evidence[0][2],
"""

    new3 = """
"shelter": wmata_evidence.get("wmata_shelter"),
"""

    text = text.replace(old3, new3)


    old4 = """
"accessible": wmata_evidence[0][3],
"""

    new4 = """
"accessible": wmata_evidence.get("wmata_accessible"),
"""

    text = text.replace(old4, new4)


    APP.write_text(text, encoding="utf-8")

    print("Updated WMATA dictionary access")


def fix_dashboard():

    text = JS.read_text(encoding="utf-8")

    # remove the obsolete endpoint call
    lines = text.splitlines()

    output = []

    for line in lines:
        if "/amenities" in line:
            print("Removing:", line)
            continue

        output.append(line)

    JS.write_text(
        "\n".join(output),
        encoding="utf-8"
    )

    print("Removed amenities references")


if __name__ == "__main__":

    backup(APP)
    backup(JS)

    fix_wmata()
    fix_dashboard()

    print("Complete")