from pathlib import Path


path = Path("src/dashboard/static/stop_detail.js")

text = path.read_text(encoding="utf-8")


marker = """
        <div class="card">

            <strong>
            Community verification
            </strong>
"""


insert = """
        <div class="card">

            <strong>
            Evidence & Data Sources
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



        <div class="card">

            <strong>
            Community verification
            </strong>
"""


if marker not in text:
    raise Exception(
        "Could not find community verification card"
    )


text = text.replace(
    marker,
    insert,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Added DDOT evidence card"
)