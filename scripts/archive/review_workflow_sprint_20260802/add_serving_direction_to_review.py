from pathlib import Path


# -------------------------
# Add API field
# -------------------------

api = Path("src/api/app.py")

text = api.read_text(
    encoding="utf-8"
)


old = """
            "county": row[7],
            "municipality": row[8],

            "streetview_url": streetview_url,
"""


new = """
            "county": row[7],
            "municipality": row[8],

            "serving_direction":
                row[11],

            "streetview_url": streetview_url,
"""


if old not in text:
    raise Exception(
        "Could not find review payload location"
    )


text = text.replace(
    old,
    new,
    1
)


api.write_text(
    text,
    encoding="utf-8"
)


# -------------------------
# Add frontend display
# -------------------------

js = Path(
    "src/dashboard/static/review_info_loader.js"
)

text = js.read_text(
    encoding="utf-8"
)


old = """
                    Jurisdiction:
                    ${info.state || ""}
                    ${info.county ? " | " + info.county : ""}
                    ${info.municipality ? " | " + info.municipality : ""}

                    <br><br>
"""


new = """
                    Jurisdiction:
                    ${info.state || ""}
                    ${info.county ? " | " + info.county : ""}
                    ${info.municipality ? " | " + info.municipality : ""}

                    <br><br>

                    Serving direction:

                    <strong>
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
                    </strong>

                    <br><br>
"""


if old not in text:
    raise Exception(
        "Could not find jurisdiction block"
    )


text = text.replace(
    old,
    new,
    1
)


js.write_text(
    text,
    encoding="utf-8"
)


print(
    "Added serving direction to review page"
)