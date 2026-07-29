from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
                                return loadEvidence(props.stop_id)
                                .then(
                                    evidence => {

                                let reviewReason =
"""

new = """
                                const evidence = {

                                    osm:
                                        detail.evidence?.osm || {},

                                    observations:
                                        detail.evidence?.reviews || [],

                                    wmata_evidence:
                                        detail.wmata_evidence || null

                                };


                                let reviewReason =
"""


if old not in text:
    raise Exception("Could not find duplicate loadEvidence block")


text = text.replace(old, new)


# remove the matching closing structure from the end of this block
old2 = """
                                    }
                                );

                            }
                        )

"""


new2 = """
                            }
                        )

"""


if old2 in text:
    text = text.replace(old2, new2, 1)


p.write_text(text)

print("Removed duplicate stop evidence fetch")
