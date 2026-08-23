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


old_wmata = '''
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
'''


new_wmata = '''
            "wmata_evidence":
                wmata_evidence,
'''


if old_wmata in text:
    text = text.replace(old_wmata, new_wmata, 1)
    print("Fixed WMATA response block")
else:
    print("WMATA block not found")


# Remove duplicate ridership entries in this response area
first = text.find('"ridership_exposure":')
second = text.find('"ridership_exposure":', first + 1)

if first != -1 and second != -1:
    # remove the second occurrence block only
    start = second
    end = text.find(",", second) + 1

    text = text[:start] + text[end:]

    print("Removed duplicate ridership key")


path.write_text(text, encoding="utf-8")

print("Done")