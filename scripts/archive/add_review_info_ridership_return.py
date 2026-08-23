from pathlib import Path
import shutil
from datetime import datetime


path = Path("src/api/app.py")

backup = path.with_name(
    f"app_before_review_return_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text()


target = """
            "wmata_evidence": {
                "wmata_stop_id": row[9],
                "wmata_status": row[10],
                "wmata_heading": row[11],
                "wmata_bench": row[12],
                "wmata_shelter": row[13],
                "wmata_accessible": row[14],
                "match_distance_m": row[15],
                "match_confidence": row[16]
            }
"""

replacement = target + """

            ,

            "ridership_exposure":
                ridership_exposure
"""


if target not in text:
    raise Exception(
        "Could not find return JSON block"
    )


text = text.replace(
    target,
    replacement,
    1
)


path.write_text(text)

print(
    "Added ridership_exposure to review info response"
)
