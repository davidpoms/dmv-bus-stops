from pathlib import Path

path = Path(
    "src/dashboard/static/review_info_loader.js"
)

text = path.read_text(
    encoding="utf-8"
)


old = """
                    ${
                        {
                            "N": "North",
                            "S": "South",
                            "E": "East",
                            "W": "West",
                            "NE": "Northeast",
                            "NW": "Northwest",
                            "SE": "Southeast",
                            "SW": "Southwest"
                        }[info.serving_direction]
                        || "Unknown"
                    }
"""


new = """
                    ${
                        (() => {
                            const heading = Number(
                                info.serving_direction
                            );

                            if (isNaN(heading)) {
                                return "Unknown";
                            }

                            if (heading < 22.5 || heading >= 337.5)
                                return "North";

                            if (heading < 67.5)
                                return "Northeast";

                            if (heading < 112.5)
                                return "East";

                            if (heading < 157.5)
                                return "Southeast";

                            if (heading < 202.5)
                                return "South";

                            if (heading < 247.5)
                                return "Southwest";

                            if (heading < 292.5)
                                return "West";

                            return "Northwest";

                        })()
                    }
"""


if old not in text:
    raise Exception(
        "Could not find direction formatter"
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
    "Updated serving direction conversion"
)