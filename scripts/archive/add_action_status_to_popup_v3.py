from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

needle = """
                                    <br><br>

                                    ${
                                        props.validation_status === "validated"
"""

insert = """
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
                                        "No active community project"
                                    }

                                    <br><br>

                                    ${
                                        props.validation_status === "validated"
"""

if needle not in text:
    print("popup insertion point not found")
    raise SystemExit(1)

text = text.replace(
    needle,
    insert,
    1
)

p.write_text(text)

print("community action added to popup")
