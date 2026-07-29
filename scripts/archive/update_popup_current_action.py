from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
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
                                        "No active community project"
                                    }

                                    <br><br>
"""

new = """
                                    <b>Community Action</b><br>

                                    ${
                                        journey.journey.current_action
                                        ?
                                        journey.journey.current_action.status
                                        :
                                        "No active community project"
                                    }

                                    <br>

                                    ${
                                        journey.journey.current_action
                                        ?
                                        journey.journey.current_action.type
                                        :
                                        ""
                                    }

                                    <br>

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
                                        ?
                                        journey.journey.current_action.notes
                                        :
                                        ""
                                    }

                                    <br><br>
"""

if old not in text:
    print("old action popup block not found")
    raise SystemExit(1)

text = text.replace(old, new, 1)

p.write_text(text)

print("popup switched to current action")
