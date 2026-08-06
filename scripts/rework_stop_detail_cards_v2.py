from pathlib import Path

path = Path("src/dashboard/static/stop_detail.js")

text = path.read_text(encoding="utf-8")


# Rename Stop ID
text = text.replace(
    "Stop ID:",
    "Internal ID:"
)


# Replace rider exposure card contents
old = """
Estimated weekday boardings:

            <strong>
            ${
                boardings
                ? Number(boardings).toLocaleString()
                : "Unknown"
            }
            </strong>


            <br><br>

            Opportunity score:

            <strong>
            ${score}
            </strong>
"""

new = """
Estimated weekday boardings:

            <strong>
            ${
                boardings
                ? Number(boardings).toLocaleString()
                : "Unknown"
            }
            </strong>


            <br><br>

            Rider exposure:

            <strong>
            ${
                review.impact_summary?.rider_exposure_percentile ||
                stop.impact_summary?.rider_exposure_percentile
                ? 
                "Higher than approximately " +
                (
                    review.impact_summary?.rider_exposure_percentile ||
                    stop.impact_summary?.rider_exposure_percentile
                ) +
                "% of regional stops"
                :
                "Unknown"
            }
            </strong>
"""


if old not in text:
    raise Exception("Rider exposure block not found")


text = text.replace(old,new)


path.write_text(text,encoding="utf-8")

print("Updated stop detail cards")