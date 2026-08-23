from pathlib import Path
import shutil
from datetime import datetime


path = Path(
    "src/dashboard/static/review_info_loader.js"
)

backup = path.with_name(
    f"review_info_loader_before_ridership_card_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text()


target = """
                    ${
                        info.streetview_url
"""


insert = """
                    ${
                        info.ridership_exposure
                        ?
                        `
                        <br><br>

                        <div class="evidence-card">

                            <strong>
                            Transit demand
                            </strong>

                            <br><br>

                            Routes serving this stop carry approximately

                            <strong>
                            ${
                                info.ridership_exposure.average_weekday_boardings.toLocaleString()
                            }
                            weekday boardings per day
                            </strong>

                            on average.

                            <br><br>

                            Routes:
                            ${
                                info.ridership_exposure.routes &&
                                info.ridership_exposure.routes.length
                                ? info.ridership_exposure.routes.join(", ")
                                : "Unknown"
                            }

                        </div>
                        `
                        :
                        ""
                    }


                    ${
                        info.streetview_url
"""


if target not in text:
    raise Exception(
        "Could not find Street View insertion point"
    )


text = text.replace(
    target,
    insert,
    1
)


path.write_text(text)

print(
    "Added transit demand card to review page"
)