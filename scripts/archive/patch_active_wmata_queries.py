from pathlib import Path
import shutil
from datetime import datetime


APP = Path("src/api/app.py")

backup = APP.with_suffix(
    f".backup_active_wmata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
)

shutil.copy(APP, backup)

text = APP.read_text(encoding="utf-8")


# ---------------------------------------------------
# PATCH 1: stop_amenities endpoint
# ---------------------------------------------------

old = """
        FROM stop_wmata_evidence
        WHERE physical_stop_id = ?
"""

new = """
        FROM active_wmata_evidence
        WHERE physical_stop_id = ?
"""


count1 = text.count(old)

text = text.replace(old,new)


# ---------------------------------------------------
# PATCH 2: review_stop_info JOIN
# ---------------------------------------------------

old2 = """
        LEFT JOIN stop_wmata_evidence w
        ON p.id = w.physical_stop_id
"""

new2 = """
        LEFT JOIN active_wmata_evidence w
        ON p.id = w.physical_stop_id
"""


count2 = text.count(old2)

text = text.replace(old2,new2)


# ---------------------------------------------------
# PATCH 3: survey endpoint WMATA query
# ---------------------------------------------------

old3 = """
        FROM stop_wmata_evidence
        WHERE physical_stop_id = ?
"""

new3 = """
        FROM active_wmata_evidence
        WHERE physical_stop_id = ?
"""


count3 = text.count(old3)

text = text.replace(old3,new3)


APP.write_text(text, encoding="utf-8")


print("Backup created:")
print(backup)

print()
print("Replacements made:")
print("stop_amenities:", count1)
print("review info join:", count2)
print("survey:", count3)