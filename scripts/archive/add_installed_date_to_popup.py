from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

needle = """
                                    ${
                                        journey.journey.current_action
                                        ?
                                        "Steward: "
                                        + journey.journey.current_action.steward
                                        :
                                        ""
                                    }

                                    <br>
"""

replacement = """
                                    ${
                                        journey.journey.current_action
                                        ?
                                        "Steward: "
                                        + journey.journey.current_action.steward
                                        :
                                        ""
                                    }

                                    <br>

                                    ${
                                        journey.journey.current_action
                                        &&
                                        journey.journey.current_action.installed_date
                                        ?
                                        "Installed: "
                                        + journey.journey.current_action.installed_date
                                        :
                                        ""
                                    }

                                    <br>
"""

if needle not in text:
    print("installed date insertion point not found")
    raise SystemExit(1)

text = text.replace(
    needle,
    replacement,
    1
)

p.write_text(text)

print("installed date added")
