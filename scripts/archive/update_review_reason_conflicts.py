from pathlib import Path
import shutil
from datetime import datetime


path = Path("src/dashboard/static/dashboard.js")

backup = path.with_name(
    f"dashboard_before_review_conflicts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text()


old = """
                                let reviewReason =
                                    "This stop has been identified as a possible opportunity for improvement. Community feedback will help determine whether riders would benefit from changes like seating, shelter, or other waiting area improvements.";


                                if (
                                    evidence.observations &&
                                    evidence.observations.length > 0
                                ) {
"""


new = """
                                let reviewReason =
                                    "This stop has been identified as a possible opportunity for improvement. Community feedback will help determine whether riders would benefit from better waiting conditions.";


                                if (
                                    detail.amenities?.wmata &&
                                    evidence.osm &&
                                    (
                                        (
                                            detail.amenities.wmata.shelter === "0" &&
                                            evidence.osm.osm_shelter === 1
                                        )
                                        ||
                                        (
                                            detail.amenities.wmata.bench === "0" &&
                                            evidence.osm.osm_bench === 1
                                        )
                                    )
                                ) {

                                    reviewReason =
                                        "Available records disagree about existing amenities at this stop. Public mapping suggests some waiting amenities may be present, while WMATA inventory does not show them. Your review will help confirm current conditions and whether additional improvements are needed.";

                                }


                                else if (
                                    evidence.observations &&
                                    evidence.observations.length > 0
                                ) {
"""


if old not in text:
    raise Exception(
        "Could not find review reason block"
    )


text = text.replace(
    old,
    new
)


path.write_text(text)

print("Updated review reason conflict handling")