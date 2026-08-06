from pathlib import Path


path = Path("src/dashboard/static/stop_detail.js")

text = path.read_text()


# Replace route formatting
old = """        const routeText =
            Array.isArray(routes)
            ? routes.join(", ")
            : routes || "No route data";
"""


new = """        const routeIds =
            stop.impact_summary?.routes ||
            review.impact_summary?.routes ||
            [];


        const routeNames =
            stop.routes ||
            review.routes ||
            [];


        const routeText =
            Array.isArray(routeIds) &&
            routeIds.length
            ?
            routeIds.map(
                (id, index) =>
                    `${id} — ${routeNames[index] || ""}`
            ).join(", ")
            :
            (
                Array.isArray(routeNames)
                ? routeNames.join(", ")
                : "No route data"
            );
"""


if old not in text:
    raise Exception("Route formatting block not found")


text = text.replace(old,new)


# Remove WMATA amenity dependency
old = """        const shelter =
            review.wmata?.shelter ??
            stop.wmata?.shelter;


        const bench =
            review.wmata?.bench ??
            stop.wmata?.bench;
"""


new = """        const hasDdotShelter =
            stop.ddot_interpretation &&
            stop.ddot_interpretation.some(
                item =>
                    item.finding.includes(
                        "active shelter"
                    )
            );
"""


if old not in text:
    raise Exception("WMATA block not found")


text = text.replace(old,new)


# Replace shelter/bench section
old = """            Shelter:

            ${
                stop.ddot_interpretation &&
                stop.ddot_interpretation.some(
                    item =>
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
"""


new = """            Shelter:

            ${
                hasDdotShelter
                ?
                "✓ Confirmed present"
                :
                "No confirmed evidence"
            }


            <br><br>

            Bench:

            No confirmed evidence
"""


if old not in text:
    raise Exception("Amenity block not found")


text = text.replace(old,new)


# Improve evidence display
old = """                          Confidence:

                      `
                  ).join("")
"""


new = """                          Confidence:
                          ${item.confidence || "unknown"}

                          <br>

                          ${
                            item.source_record
                            ?
                            "Source ID: " + item.source_record
                            :
                            ""
                          }

                          <br>

                          Routes:
                          ${
                            item.routes?.join(", ")
                            || "None"
                          }

                          </div>
                          <br>

                      `
                  ).join("")
"""


if old not in text:
    raise Exception("Evidence rendering block not found")


text = text.replace(old,new)


path.write_text(text)

print("Updated stop detail cards")