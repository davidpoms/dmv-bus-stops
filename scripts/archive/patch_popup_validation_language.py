from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
                                    <b>Opportunity Signal</b><br>

                                    Rider impact:
                                    ${props.impact}<br>

                                    This stop is being evaluated through
                                    community verification.
                                    <br>
"""


new = """
                                    <b>Community Evidence Status</b><br>

                                    ${
                                        props.validation_status === "validated"
                                        ?
                                        "Validated candidate for community action"
                                        :
                                        "Awaiting community validation"
                                    }
                                    <br><br>

                                    ${
                                        props.validation_status === "validated"
                                        ?
                                        `
                                        Rider impact signal:
                                        ${props.impact}<br>
                                        `
                                        :
                                        `
                                        Impact estimates are hidden until
                                        volunteer evidence review is complete.
                                        <br>
                                        `
                                    }
"""


if old not in text:
    print("popup evidence block not found")
    raise SystemExit(1)

text = text.replace(old, new)

p.write_text(text)

print("popup validation language patched")
