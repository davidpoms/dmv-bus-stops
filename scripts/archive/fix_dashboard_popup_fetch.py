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
                            fetch(`/stops/${props.stop_id}`)
                                .then(response => response.json()),

                                .then(response => {
                                    if (!response.ok) {
                                        return {
                                            wmata: null,
                                            osm: null
                                        };
                                    }

                                    return response.json();
                                })
                        ])

                        .then(
                            ([detail, amenities]) => {

                                detail.amenities = amenities;
"""


new = """
                        fetch(`/stops/${props.stop_id}`)
                        .then(response => response.json())

                        .then(
                            (detail) => {

                                detail.amenities = {
                                    wmata:
                                        detail.wmata_evidence
                                };
"""


if old in text:
    text = text.replace(old, new)
    print("Fixed dashboard stop fetch")
else:
    print("Exact block not found")


path.write_text(text, encoding="utf-8")

print("Complete")