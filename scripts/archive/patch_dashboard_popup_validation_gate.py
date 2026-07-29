from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
                                    <b>Opportunity Signal</b><br>

                                    Score:
                                    ${props.score}<br>

                                    Impact:
                                    ${props.impact}<br>
"""


new = """
                                    <b>Community Evidence Status</b><br>

                                    ${
                                        props.validation_status === "validated"
                                        ?
                                        `
                                        Validated candidate<br><br>

                                        <b>Opportunity Signal</b><br>

                                        Score:
                                        ${props.score}<br>

                                        Impact:
                                        ${props.impact}<br>
                                        `
                                        :
                                        `
                                        Awaiting community validation<br><br>

                                        Scores and impact estimates will appear
                                        after volunteer evidence review.
                                        `
                                    }
"""


if old not in text:
    print("popup opportunity block not found")
    raise SystemExit(1)


text = text.replace(old, new)

p.write_text(text)

print("popup validation gate patched")
