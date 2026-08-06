from pathlib import Path

path = Path("src/dashboard/static/review_info_loader.js")

text = path.read_text()


marker = """
                    ${
                        info.wmata
"""


insert = r"""
                    ${
                        info.impact_summary
                        ?
                        `
                        <div class="evidence-card">

                            <strong>
                            Why this stop is being reviewed
                            </strong>

                            <br><br>

                            This stop has been identified as a

                            <strong>
                            ${info.impact_summary.impact_level.replace("_", " ")}
                            </strong>

                            improvement opportunity.

                            <br><br>

                            Estimated rider exposure:

                            <strong>
                            ${
                                Math.round(
                                    info.impact_summary.daily_route_exposure
                                ).toLocaleString()
                            }
                            riders per day
                            </strong>

                            <br><br>

                            Recommended action:

                            ${
                                info.impact_summary.recommendations.length
                                ? info.impact_summary.recommendations
                                    .map(r => r.replaceAll("_", " "))
                                    .join(", ")
                                : "Community review needed"
                            }

                        </div>

                        <br>
                        `
                        :
                        ""
                    }


""" + marker


if marker not in text:
    raise Exception("Could not find WMATA insertion point")


text = text.replace(marker, insert, 1)

path.write_text(text)

print("Added impact summary card")