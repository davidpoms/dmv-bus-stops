from pathlib import Path

path = Path("src/dashboard/static/review_info_loader.js")

text = path.read_text()


start_marker = """
                    ${
                        info.impact_summary &&
                        info.impact_summary.rider_exposure_percentile
"""

end_marker = """
                    ${
                        info.wmata
"""


start = text.find(start_marker)

if start == -1:
    raise Exception("Could not find impact card start")


end = text.find(end_marker, start)

if end == -1:
    raise Exception("Could not find WMATA card boundary")


replacement = r"""
                    ${
                        info.impact_summary &&
                        info.impact_summary.rider_exposure_percentile
                        ?
                        `
                        <div class="evidence-card">

                            <strong>
                            Why this stop was prioritized
                            </strong>

                            <br><br>

                            Verification priorities consider rider exposure
                            and the need for better information about current
                            stop conditions.

                            <br><br>

                            <strong>
                            Rider exposure
                            </strong>

                            <br><br>

                            The routes serving this stop carry more riders
                            than approximately

                            <strong>
                            ${info.impact_summary.rider_exposure_percentile}%
                            </strong>

                            of stops in the region.

                            <br><br>

                            <small>
                            Rider exposure is estimated using route-level
                            ridership data associated with this stop.
                            Stop-level boarding counts are not available.
                            </small>

                        </div>

                        <br>
                        `
                        :
                        ""
                    }


                    ${
                        info.impact_summary
                        ?
                        `
                        <div class="evidence-card">

                            <strong>
                            Why this stop needs verification
                            </strong>

                            <br><br>

                            Available records do not fully confirm current
                            waiting conditions.

                            <br><br>

                            Your review helps improve the accuracy of stop
                            information and identify where improvements may
                            be needed.

                        </div>

                        <br>
                        `
                        :
                        ""
                    }


"""

new_text = text[:start] + replacement + text[end:]

path.write_text(new_text)

print("Cleaned review info cards")