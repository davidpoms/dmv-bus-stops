from pathlib import Path
import shutil
from datetime import datetime


path = Path("src/dashboard/static/dashboard.js")

backup = path.with_name(
    f"dashboard_before_evidence_note_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text()


old = """
                                        Bench mapped:
                                        ${
                                            evidence.osm.osm_bench === 1
                                            ? "Yes"
                                            : "No"
                                        }<br>

                                        `;
"""


new = """
                                        Bench mapped:
                                        ${
                                            evidence.osm.osm_bench === 1
                                            ? "Yes"
                                            : "No"
                                        }<br>


                                        ${
                                            detail.amenities?.wmata &&
                                            (
                                                (
                                                    detail.amenities.wmata.shelter === "1" &&
                                                    evidence.osm.osm_shelter === 0
                                                )
                                                ||
                                                (
                                                    detail.amenities.wmata.shelter !== "1" &&
                                                    evidence.osm.osm_shelter === 1
                                                )
                                            )
                                            ?
                                            `
                                            <br>
                                            <b>Data note:</b><br>
                                            WMATA inventory and public mapping sources differ on shelter status. A community review can help confirm current waiting conditions.<br>
                                            `
                                            :
                                            ""
                                        }

                                        `;
"""


if old not in text:
    raise Exception(
        "Could not find public mapping block"
    )


text = text.replace(old, new)


path.write_text(text)


print("Added evidence conflict note")