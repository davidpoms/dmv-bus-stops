from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
                                    <b>Community Evidence Status</b><br>

                                    ${
                                        props.validation_status === "validated"
                                        ?
                                        "Validated candidate for action"
                                        :
                                        "Evidence being gathered"
                                    }
                                    <br><br>

                                    Rider impact signal:
                                    ${props.impact}<br>
"""

new = """
                                    <b>Community Evidence Status</b><br>

                                    ${
                                        props.validation_status === "validated"
                                        ?
                                        "Validated candidate for action"
                                        :
                                        "Evidence being gathered"
                                    }
                                    <br><br>

                                    <b>Community Action</b><br>

                                    ${
                                        props.action_status === "installed"
                                        ?
                                        "Improvement installed"
                                        :
                                        props.action_status === "planned"
                                        ?
                                        "Community project planned"
                                        :
                                        "No project started"
                                    }
                                    <br><br>

                                    Rider impact signal:
                                    ${props.impact}<br>
"""

if old not in text:
    print("popup block not found")
    raise SystemExit(1)

text = text.replace(old, new)

p.write_text(text)

print("action status added to popup")
