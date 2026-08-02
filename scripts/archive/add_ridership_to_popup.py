from pathlib import Path
from datetime import datetime
import shutil


path = Path("src/dashboard/static/dashboard.js")

backup = path.with_name(
    f"dashboard_before_ridership_popup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

print("Backup:", backup)

shutil.copy(path, backup)


text = path.read_text(encoding="utf-8")


marker = """
                                let popup = `
                                <b>${props.location.replace("+", " at ")}</b><br>
"""


insert = """
                                let popup = `
                                <b>${props.location.replace("+", " at ")}</b><br>

                                <br>

                                <b>Transit demand</b><br>

                                Weekday riders exposed:
                                ${
                                    detail.ridership_exposure
                                    ? detail.ridership_exposure.weekday_boardings.toLocaleString()
                                    : "Unknown"
                                }

                                <br>

                                Routes:
                                ${
                                    detail.ridership_exposure &&
                                    detail.ridership_exposure.routes.length
                                    ? detail.ridership_exposure.routes.join(", ")
                                    : "Unknown"
                                }

                                <br><br>
"""


if marker not in text:
    raise Exception(
        "Could not find popup insertion point"
    )


text = text.replace(
    marker,
    insert,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print("Added ridership information to popup")