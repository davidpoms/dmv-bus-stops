from pathlib import Path

path = Path("src/dashboard/static/stop_detail.js")

text = path.read_text(encoding="utf-8")


old = """
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
"""


new = """
                        Confidence:

                        <strong>
                        ${item.confidence || "unknown"}
                        </strong>


                        <br><br>

                        Source record:

                        <strong>
                        ${item.source_record || "unknown"}
                        </strong>


                        ${
                            item.source_type
                            ?

                            `<br>
                            Source type:
                            <strong>
                            ${item.source_type}
                            </strong>`

                            :

                            ""
                        }


                        ${
                            item.routes &&
                            item.routes.length
                            ?

                            `<br>
                            Routes:
                            <strong>
                            ${item.routes.join(", ")}</strong>`

                            :

                            ""
                        }


                    </div>
"""


if old not in text:
    raise Exception(
        "DDOT evidence confidence section not found"
    )


text = text.replace(old, new)


path.write_text(text, encoding="utf-8")

print("Updated DDOT evidence card")