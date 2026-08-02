from pathlib import Path
from datetime import datetime
import shutil


path = Path(
    "src/dashboard/static/review_stop.js"
)


backup = path.with_name(
    f"review_stop_before_ridership_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(
    path,
    backup
)

print("Backup:", backup)


text = path.read_text(
    encoding="utf-8"
)


needle = """
                Stop ID: ${data.stop_id}

                <br><br>
"""


replacement = """
                Stop ID: ${data.stop_id}

                <br><br>


                ${
                    data.ridership_exposure
                    ?
                    `
                    <strong>Transit demand</strong>
                    <br><br>

                    Routes serving this stop carry approximately

                    <strong>
                    ${data.ridership_exposure.average_weekday_boardings.toLocaleString()}
                    weekday boardings per day
                    </strong>

                    on average.

                    <br>

                    Routes:
                    ${data.ridership_exposure.routes.join(", ")}

                    <br><br>
                    `
                    :
                    ""
                }
"""


if needle not in text:
    raise Exception(
        "Could not find insertion point"
    )


text = text.replace(
    needle,
    replacement,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Added ridership information to review page"
)