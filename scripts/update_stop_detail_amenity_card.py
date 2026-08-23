from pathlib import Path


path = Path("src/dashboard/static/stop_detail.js")

text = path.read_text(encoding="utf-8")


old = """
        <div class="card">

            <strong>
            Current stop information
            </strong>


            <br><br>

            WMATA status:

            ${
                review.wmata?.status ||
                stop.wmata?.status ||
                "Unknown"
            }


            <br><br>

            Shelter:

            ${
                shelter == 1 || shelter === "yes"
                ? "Yes"
                : "No"
            }


            <br>

            Bench:

            ${
                bench == 1 || bench === "yes"
                ? "Yes"
                : "No"
            }


        </div>
"""


new = """
        <div class="card">

            <strong>
            Amenity status
            </strong>


            <br><br>

            Shelter:

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


            <br><br>

            Primary source:

            ${
                stop.ddot_interpretation &&
                stop.ddot_interpretation.length
                ?

                stop.ddot_interpretation[0].source

                :

                "No verified source"
            }


        </div>
"""


if old not in text:
    raise Exception(
        "Could not find Current stop information card"
    )


text = text.replace(
    old,
    new,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Updated stop detail amenity card"
)