from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
                                if (
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 1 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "This stop appears to have a shelter, but seating information needs verification. Your review will help confirm whether riders have a place to sit while waiting.";

                                }


                                else if (
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 0 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "This stop does not appear to have a shelter or bench. Your review will help determine whether riders would benefit from improved waiting conditions.";

                                }


                                else if (
                                    evidence.observations &&
                                    evidence.observations.length > 0
                                ) {

                                    reviewReason =
                                        "Community members have already provided feedback about this stop. Additional observations help confirm improvement needs.";

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
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 1 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "This stop appears to have a shelter, but seating information needs verification. Your review will help confirm whether riders have a place to sit while waiting.";

                                }


                                else if (
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 0 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "This stop does not appear to have a shelter or bench. Your review will help determine whether riders would benefit from improved waiting conditions.";

                                }
"""


if old not in text:
    raise Exception(
        "Could not find reviewReason condition block"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Prioritized community reviews in popup explanation"
)
