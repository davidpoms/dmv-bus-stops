from pathlib import Path
import shutil
from datetime import datetime


path = Path("src/api/app.py")

backup = path.with_suffix(
    path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text(encoding="utf-8")


old = """
"wmata_evidence": (
    {
        "status": wmata_evidence[0][0],
        "bench": wmata_evidence[0][1],
        "shelter": wmata_evidence[0][2],
        "accessible": wmata_evidence[0][3],
        "confidence": wmata_evidence[0][4],
        "distance_meters": wmata_evidence[0][5]
    }
    if wmata_evidence
    else None
),
"""


new = """
"wmata_evidence": wmata_evidence,
"""


if old not in text:
    print("Could not find exact block")
else:
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("Fixed WMATA evidence block")