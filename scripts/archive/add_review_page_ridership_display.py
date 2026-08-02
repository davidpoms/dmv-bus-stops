from pathlib import Path
from datetime import datetime
import shutil


path = Path("src/dashboard/static/review_info_loader.js")


backup = path.with_name(
    f"review_info_loader_before_ridership_display_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text()


needle = """
                    <br><br>

                    ${
                        info.wmata
"""


insert = """
                    <br><br>


                    ${
                        info.ridership_exposure
                        ?
                        `
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
                                info.ridership_exposure.routes.length
                                ? info.ridership_exposure.routes.join(", ")
                                : "Unknown"
                            }

                        </div>

                        <br>
                        `
                        :
                        ""
                    }


                    ${
                        info.wmata
"""


if needle not in text:
    raise Exception(
        "Could not find insertion point"
    )


text = text.replace(
    needle,
    insert,
    1
)


path.write_text(text)

print(
    "Added ridership display to review page"
)