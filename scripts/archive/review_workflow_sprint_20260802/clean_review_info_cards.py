from pathlib import Path

path = Path("src/dashboard/static/review_info_loader.js")

text = path.read_text()


start = text.find(
"""
                    ${
                        info.impact_summary
                        ?
                        `
                        <div class="evidence-card">

                            <strong>
                            Why this stop is being reviewed
"""
)

if start == -1:
    raise Exception("Could not find old impact card")


end = text.find(
"""
                    ${
                        info.wmata
""",
    start
)

if end == -1:
    raise Exception("Could not find WMATA insertion point")


replacement = """
                    ${
                        info.impact_summary
                        ?
                        `
                        <div class="evidence-card">

                            <strong>
                            Why this stop needs verification
                            </strong>

                            <br><br>

                            Available records do not fully confirm
                            current waiting conditions.

                            Your review helps improve the accuracy of
                            stop information and identify where improvements
                            may be needed.

                        </div>

                        <br>
                        `
                        :
                        ""
                    }


"""


text = text[:start] + replacement + text[end:]


# remove duplicate transit demand card

start = text.find(
"""
                    ${
                        info.ridership_exposure
"""
)

if start != -1:

    end = text.find(
"""
                    ${
                        info.impact_summary &&
""",
        start
    )

    if end == -1:
        raise Exception("Could not find next card after ridership card")

    text = text[:start] + text[end:]


path.write_text(text)

print("Cleaned review info cards")