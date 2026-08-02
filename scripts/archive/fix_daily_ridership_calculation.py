from pathlib import Path
from datetime import datetime
import shutil


path = Path("src/api/app.py")


backup = path.with_name(
    f"app_before_daily_ridership_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text(encoding="utf-8")


old = """
            "weekday_boardings":
                round(ridership[0][0])
                if ridership[0][0]
                else 0,
"""


new = """
            "weekday_boardings_total":
                round(ridership[0][0])
                if ridership[0][0]
                else 0,

            "average_weekday_boardings":
                round(ridership[0][0] / 23)
                if ridership[0][0]
                else 0,
"""


if old not in text:
    raise Exception(
        "Could not find ridership payload"
    )


text = text.replace(old, new, 1)


path.write_text(text, encoding="utf-8")


print("Updated ridership calculation")