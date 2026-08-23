from pathlib import Path


path = Path(
    "src/dashboard/static/review_info_loader.js"
)

text = path.read_text(
    encoding="utf-8"
)


old = """
                            <br><br>

                            <small>
                            Rider exposure is estimated using route-level
                            ridership data associated with this stop.
                            Stop-level boarding counts are not available.
                            </small>
"""


new = """
                            <br><br>

                            Estimated route exposure:

                            <strong>
                            ${
                                info.impact_summary.estimated_weekday_boardings
                                ? info.impact_summary.estimated_weekday_boardings.toLocaleString()
                                : "Unknown"
                            }
                            weekday boardings across
                            ${
                                info.impact_summary.routes_served || 0
                            }
                            serving routes
                            </strong>

                            <br><br>

                            Routes:

                            ${
                                info.impact_summary.routes &&
                                info.impact_summary.routes.length
                                ? info.impact_summary.routes.join(", ")
                                : "Unknown"
                            }

                            <br><br>

                            <small>
                            Rider exposure is estimated using route-level
                            ridership data associated with this stop.
                            Stop-level boarding counts are not available.
                            </small>
"""


if old not in text:
    raise Exception(
        "Could not find rider exposure qualifier block"
    )


text = text.replace(
    old,
    new
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Restored ridership context to priority card"
)