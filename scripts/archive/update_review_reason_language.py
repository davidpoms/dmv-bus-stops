from pathlib import Path
from datetime import datetime
import shutil


path = Path("src/dashboard/static/dashboard.js")


backup = path.with_name(
    f"dashboard_before_review_reason_language_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text(encoding="utf-8")


old = """
                                if (
                                    evidence.observations &&
                                    evidence.observations.length > 0
                                ) {

                                    reviewReason =
                                        "Community members have already provided feedback about this stop. Additional observations help confirm improvement needs.";

                                }


                                else if (
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 1 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "This stop appears to have a shelter, but seating information needs verification. Your review will help confirm whether riders have a place to sit while waiting.";

                                }


                                else if (
                                    detail.amenities?.wmata?.shelter === "1"
                                ) {

                                    reviewReason =
                                        "Available records indicate this stop has a shelter, but seating information or rider experience may need verification.";

                                }


                                else if (
                                    detail.amenities?.wmata?.shelter !== "1" &&
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 0 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "Available records do not show a shelter or bench. Your review will help determine whether riders would benefit from improved waiting conditions.";

                                }
"""


new = """
                                if (
                                    evidence.observations &&
                                    evidence.observations.length > 0
                                ) {

                                    reviewReason =
                                        "Community members have already provided feedback about this stop. Additional observations help confirm improvement needs.";

                                }


                                else if (
                                    detail.wmata_evidence &&
                                    (
                                        detail.wmata_evidence.wmata_shelter === "1" ||
                                        detail.wmata_evidence.shelter === "1"
                                    )
                                ) {

                                    reviewReason =
                                        "Available records indicate this stop likely has a shelter. Your review will help determine whether additional improvements, such as seating, accessibility features, or other waiting area enhancements, would better support riders.";

                                }


                                else if (
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 1 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "This stop appears to have a shelter, but seating information needs verification. Your review will help determine whether riders have adequate places to sit while waiting.";

                                }


                                else if (
                                    detail.wmata_evidence &&
                                    detail.wmata_evidence.wmata_shelter === "0" &&
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 0 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "Available records do not show a shelter or bench. Your review will help determine whether riders would benefit from improved waiting conditions.";

                                }
"""


if old not in text:
    raise Exception(
        "Could not find review reason block"
    )


text = text.replace(
    old,
    new
)


path.write_text(
    text,
    encoding="utf-8"
)


print("Updated review reason language")