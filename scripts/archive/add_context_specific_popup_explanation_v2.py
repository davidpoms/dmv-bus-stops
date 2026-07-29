from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


marker = """
                                let popup = `
"""


insert = """
                                let reviewReason =
                                    "This stop has been identified as a possible opportunity for improvement. Community feedback will help determine whether riders would benefit from changes like seating, shelter, or other waiting area improvements.";


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


if marker not in text:
    raise Exception(
        "Could not find popup insertion point"
    )


if "let reviewReason =" in text:
    raise Exception(
        "Context explanation already added"
    )


text = text.replace(
    marker,
    insert + marker,
    1
)


old_text = """
                                This stop has been identified as a possible
                                opportunity for improvement. Community feedback
                                will help determine whether riders would benefit
                                from changes like seating, shelter, or other
                                waiting area improvements.
"""


new_text = """
                                ${reviewReason}
"""


if old_text in text:
    text = text.replace(
        old_text,
        new_text
    )


p.write_text(text)

print(
    "Added context-specific popup explanation logic"
)
