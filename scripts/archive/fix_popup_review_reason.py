from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
                                else if (
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 0 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "This stop does not appear to have a shelter or bench. Your review will help determine whether riders would benefit from improved waiting conditions.";

                                }
"""


new = """
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


if old not in text:
    raise Exception("Target block not found")


text = text.replace(old,new)

p.write_text(text)

print("Updated review reason logic")
