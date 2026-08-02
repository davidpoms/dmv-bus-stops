from pathlib import Path
from datetime import datetime
import shutil


path = Path("src/dashboard/static/dashboard.js")


backup = path.with_name(
    f"dashboard_before_daily_ridership_field_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text(encoding="utf-8")


old = """
detail.ridership_exposure.weekday_boardings.toLocaleString()
"""


new = """
detail.ridership_exposure.average_weekday_boardings.toLocaleString()
"""


if old not in text:
    raise Exception(
        "Could not find old ridership field"
    )


text = text.replace(
    old,
    new
)


old_phrase = """
weekday riders.
"""


new_phrase = """
average weekday riders per day.
"""


text = text.replace(
    old_phrase,
    new_phrase
)


path.write_text(
    text,
    encoding="utf-8"
)


print("Updated popup ridership wording")