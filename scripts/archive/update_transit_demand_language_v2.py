from pathlib import Path
from datetime import datetime
import shutil


path = Path("src/dashboard/static/dashboard.js")


backup = path.with_name(
    f"dashboard_before_transit_demand_update_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text(encoding="utf-8")


start_marker = """
                                <b>Transit demand</b><br>
"""


end_marker = """
                                Routes:
"""


start = text.find(start_marker)

if start == -1:
    raise Exception(
        "Could not find Transit demand start"
    )


end = text.find(
    end_marker,
    start
)

if end == -1:
    raise Exception(
        "Could not find Routes section"
    )


replacement = """
                                <b>Transit demand</b><br>

                                Routes serving this stop carry approximately

                                <b>
                                ${
                                    detail.ridership_exposure
                                    ? detail.ridership_exposure.average_weekday_boardings.toLocaleString()
                                    : "Unknown"
                                }
                                weekday boardings per day
                                </b>

                                on average.

                                <br><br>

"""


text = (
    text[:start]
    +
    replacement
    +
    text[end:]
)


path.write_text(
    text,
    encoding="utf-8"
)


print("Updated transit demand section")