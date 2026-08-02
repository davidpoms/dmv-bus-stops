from pathlib import Path
from datetime import datetime
import shutil


path = Path("src/dashboard/static/dashboard.js")


backup = path.with_name(
    f"dashboard_before_daily_ridership_field_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text(encoding="utf-8")


old = """
${
                                    detail.ridership_exposure
                                    ? detail.ridership_exposure.weekday_boardings.toLocaleString()
                                    : "Unknown"
                                }
"""


new = """
${
                                    detail.ridership_exposure
                                    ? detail.ridership_exposure.average_weekday_boardings.toLocaleString()
                                    : "Unknown"
                                }
"""


if old not in text:
    raise Exception(
        "Could not find ridership template block"
    )


text = text.replace(
    old,
    new,
    1
)


text = text.replace(
    "weekday riders.",
    "average weekday riders per day.",
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print("Updated popup ridership field")