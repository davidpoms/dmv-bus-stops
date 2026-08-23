from pathlib import Path
from datetime import datetime
import shutil


path = Path("src/dashboard/static/dashboard.js")


backup = path.with_name(
    f"dashboard_before_ridership_language_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

print("Backup:", backup)

shutil.copy(path, backup)


text = path.read_text(encoding="utf-8")


old = """
                                Weekday riders exposed:
                                ${
                                    detail.ridership_exposure
                                    ? detail.ridership_exposure.weekday_boardings.toLocaleString()
                                    : "Unknown"
                                }

                                <br>

                                Routes:
"""


new = """
                                This stop serves routes that average approximately

                                <b>
                                ${
                                    detail.ridership_exposure
                                    ? detail.ridership_exposure.weekday_boardings.toLocaleString()
                                    : "Unknown"
                                }
                                </b>

                                weekday riders.

                                <br>

                                Routes:
"""


if old not in text:
    raise Exception(
        "Could not find old ridership language"
    )


text = text.replace(
    old,
    new,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print("Updated ridership language")