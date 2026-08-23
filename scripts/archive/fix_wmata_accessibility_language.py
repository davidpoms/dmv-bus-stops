from pathlib import Path
import shutil
from datetime import datetime


path = Path(
    "src/dashboard/static/dashboard.js"
)

backup = path.with_name(
    f"dashboard_before_accessibility_language_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(
    path,
    backup
)

print("Backup:", backup)


text = path.read_text(
    encoding="utf-8"
)


old = """
                                        Accessible boarding:
                                        ${
                                            detail.amenities.wmata.accessible === "Y"
                                            ? "Yes"
                                            : "No"
                                        }<br>
"""


new = """
                                        WMATA accessibility rating:
                                        ${
                                            detail.amenities.wmata.accessible === "Y"
                                            ? "Accessible"
                                            : detail.amenities.wmata.accessible === "N"
                                            ? "Not rated accessible"
                                            : "Unknown"
                                        }<br>
"""


if old not in text:
    raise Exception(
        "Could not find accessibility display block"
    )


text = text.replace(
    old,
    new
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Updated WMATA accessibility language"
)
