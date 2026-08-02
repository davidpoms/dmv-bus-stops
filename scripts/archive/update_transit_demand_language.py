from pathlib import Path
from datetime import datetime
import shutil
import re


path = Path("src/dashboard/static/dashboard.js")


backup = path.with_name(
    f"dashboard_before_transit_demand_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text(encoding="utf-8")


pattern = r"""
                                <b>Transit demand</b><br>

                                This stop serves routes that average approximately

                                <b>
                                \$\{
                                    detail\.ridership_exposure
                                    \? detail\.ridership_exposure\.weekday_boardings\.toLocaleString\(\)
                                    : "Unknown"
                                \}
                                </b>

                                weekday riders\.

                                <br>
"""


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

                                <br>
"""


new_text, count = re.subn(
    pattern,
    replacement,
    text,
    flags=re.VERBOSE
)


if count == 0:
    raise Exception(
        "Could not find transit demand section"
    )


path.write_text(
    new_text,
    encoding="utf-8"
)


print("Updated transit demand wording")