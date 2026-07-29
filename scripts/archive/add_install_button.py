from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

needle = """
                                                journey.journey.current_action.status === "planned"
                                                ?
                                                "Project planned"
"""

replacement = """
                                                journey.journey.current_action.status === "planned"
                                                ?
                                                `
                                                Project planned
                                                <br>
                                                <button
                                                    class="installStopButton"
                                                    data-stop="${props.stop_id}">
                                                    Mark installed
                                                </button>
                                                `
"""

if needle not in text:
    print("planned action block not found")
    raise SystemExit(1)

text = text.replace(
    needle,
    replacement,
    1
)

p.write_text(text)

print("install button added")
