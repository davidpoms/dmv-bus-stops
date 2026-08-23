from pathlib import Path


path = Path("src/dashboard/static/stop_detail.js")

text = path.read_text(encoding="utf-8")


# Rename Stop ID label
text = text.replace(
    "Stop ID:",
    "Internal ID:"
)


# Replace the entire rider exposure + amenity + evidence section
start_marker = """
        <div class="card">

            <strong>Rider exposure</strong>
"""

end_marker = """
        <div class="card">

            <strong>
            Community verification
"""

start = text.find(start_marker)

end = text.find(end_marker)


if start == -1:
    raise Exception("Could not find rider exposure card start")

if end == -1:
    raise Exception("Could not find community verification card")


replacement = r"""
        <div class="card">

            <strong>
            Stop information
            </strong>

            <br><br>


            Routes served:

            <strong>
            ${routeText}
            </strong>


            <br><br>


            Estimated weekday boardings:

            <strong>
            ${
                boardings
                ? Number(boardings).toLocaleString()
                : "Unknown"
            }
            </strong>


            <br><br>


            Rider exposure percentile:

            <strong>
            ${
                stop.impact_summary?.rider_exposure_percentile
                ?
                stop.impact_summary.rider_exposure_percentile + "th percentile"
                :
                "Unknown"
            }
            </strong>


            <br><br>


            Opportunity score:

            <strong>
            ${score}
            </strong>


            <br><br>


            <strong>
            Amenity status
            </strong>


            <br><br>


            Shelter:

            ${
                stop.ddot_interpretation &&
                stop.ddot_interpretation.some(
                    item =>
                    item.finding &&
                    item.finding.includes(
                        "active shelter"
                    )
                )
                ?
                "✓ Confirmed present"
                :
                "No confirmed evidence"
            }


            <br><br>


            Bench:

            No confirmed evidence


            <br><br>


            <strong>
            Evidence sources
            </strong>


            <br><br>


            ${
                stop.ddot_interpretation &&
                stop.ddot_interpretation.length
                ?

                stop.ddot_interpretation.map(
                    item => `

                    <div>

                        <strong>
                        ${item.source}
                        </strong>

                        <br>

                        ${item.finding}

                        <br>

                        Confidence:

                        <strong>
                        ${item.confidence}
                        </strong>


                        ${
                            item.source_record
                            ?
                            `<br>
                            Source record:
                            ${item.source_record}`
                            :
                            ""
                        }


                        ${
                            item.routes &&
                            item.routes.length
                            ?
                            `<br>
                            Routes:
                            ${item.routes.join(", ")}`
                            :
                            ""
                        }

                    </div>

                    <br>

                    `
                ).join("")

                :

                "No external evidence available."

            }


        </div>


"""


text = (
    text[:start]
    +
    replacement
    +
    text[end:]
)


path.write_text(text, encoding="utf-8")

print("Updated stop detail cards")