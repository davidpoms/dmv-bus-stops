from pathlib import Path

js = Path("src/dashboard/static/dashboard.js")

text = js.read_text(encoding="utf-8")


old = """
                                <b>
                                ${
                                    detail.ridership_exposure
                                    ? detail.ridership_exposure.average_weekday_boardings.toLocaleString()
                                    : "Unknown"
                                }
                                weekday boardings per day
                                </b>
"""

new = """
                                <b>
                                ${
                                    detail.impact_summary
                                    ? detail.impact_summary.estimated_weekday_boardings.toLocaleString()
                                    : "Unknown"
                                }
                                weekday boardings per day
                                </b>
"""


if old not in text:
    raise RuntimeError("Could not find weekday exposure block")

text = text.replace(old, new)


old_routes = """
                                ${
                                    detail.ridership_exposure &&
                                    detail.ridership_exposure.routes.length
                                    ? detail.ridership_exposure.routes.join(", ")
                                    : "Unknown"
                                }
"""

new_routes = """
                                ${
                                    detail.impact_summary &&
                                    detail.impact_summary.routes.length
                                    ? detail.impact_summary.routes.join(", ")
                                    : "Unknown"
                                }
"""


if old_routes not in text:
    raise RuntimeError("Could not find routes block")

text = text.replace(old_routes, new_routes)


marker = """
                                <br><br>

                                <b>WMATA Stop IDs:</b>
"""


insert = """
                                <br><br>

                                <b>Rider exposure percentile:</b>
                                ${
                                    detail.impact_summary &&
                                    detail.impact_summary.rider_exposure_percentile !== null
                                    ? detail.impact_summary.rider_exposure_percentile + "th percentile"
                                    : "Unknown"
                                }

"""


if "Rider exposure percentile:" not in text:

    if marker not in text:
        raise RuntimeError("Could not find WMATA marker")

    text = text.replace(marker, insert + marker)


js.write_text(text, encoding="utf-8")

print("Updated dashboard popup ridership display.")