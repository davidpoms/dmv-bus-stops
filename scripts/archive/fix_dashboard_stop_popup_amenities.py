from pathlib import Path
import shutil
from datetime import datetime

path = Path("src/dashboard/static/dashboard.js")

backup = path.with_suffix(
    path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)

shutil.copy(path, backup)

print("Backup:", backup)

text = path.read_text(encoding="utf-8")


old = """
        Promise.all([
            fetch(`/stops/${stopId}`).then(r => r.json()),
            fetch(`/stops/${stopId}/amenities`).then(r => r.json())
        ])
        .then(
            ([detail, amenities]) => {

                detail.amenities = amenities;
"""


new = """
        fetch(`/stops/${stopId}`)
        .then(r => r.json())
        .then(
            (detail) => {

                detail.amenities = {
                    wmata: detail.wmata_evidence
                };
"""


if old in text:
    text = text.replace(old, new)
    print("Replaced amenities fetch")
else:
    print("Could not find amenities fetch block")


path.write_text(text, encoding="utf-8")

print("Complete")