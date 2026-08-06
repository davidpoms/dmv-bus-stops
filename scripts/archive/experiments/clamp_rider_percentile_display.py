from pathlib import Path

path = Path(
    "src/dashboard/static/review_info_loader.js"
)

text = path.read_text(
    encoding="utf-8"
)


old = """
                            ${info.impact_summary.rider_exposure_percentile}%
"""


new = """
                            ${
                                Math.min(
                                    info.impact_summary.rider_exposure_percentile,
                                    99
                                )
                            }%
"""


if old not in text:
    raise Exception(
        "Could not find percentile display"
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
    "Clamped rider exposure percentile display"
)