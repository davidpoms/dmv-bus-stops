from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

needle = """
                                    ${
                                        journey.journey.current_action
                                        ?
                                        journey.journey.current_action.notes
                                        :
                                        ""
                                    }

                                    <br><br>
"""

replacement = """
                                    ${
                                        journey.journey.current_action
                                        ?
                                        journey.journey.current_action.notes
                                        :
                                        ""
                                    }

                                    <br><br>

                                    <b>Volunteer Actions</b><br>

                                    ${
                                        props.validation_status !== "validated"
                                        ?
                                        "Awaiting validation before adoption"
                                        :
                                        journey.journey.current_action
                                        ?
                                            (
                                                journey.journey.current_action.status === "planned"
                                                ?
                                                "Project planned"
                                                :
                                                journey.journey.current_action.status === "installed"
                                                ?
                                                "Project completed"
                                                :
                                                "Action in progress"
                                            )
                                        :
                                        `
                                        <button
                                            class="adoptStopButton"
                                            data-stop="${props.stop_id}">
                                            Adopt this stop
                                        </button>
                                        `
                                    }

                                    <br><br>
"""

if needle not in text:
    print("button insertion point not found")
    raise SystemExit(1)

text = text.replace(
    needle,
    replacement,
    1
)

p.write_text(text)

print("popup action buttons added")
