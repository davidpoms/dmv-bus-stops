from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
                                    Rider impact signal:
                                    ${props.impact}<br>
"""

new = """
                                    Rider impact signal:
                                    ${props.impact}<br>

                                    <br>

                                    <b>Community Action</b><br>

                                    ${
                                        props.action_status === "installed"
                                        ?
                                        "Bench or improvement installed"
                                        :
                                        props.action_status === "planned"
                                        ?
                                        "Community project planned"
                                        :
                                        "No active project"
                                    }
                                    <br>
"""

if old not in text:
    print("popup action block not found")
else:
    text = text.replace(old, new, 1)
    p.write_text(text)
    print("action status added to popup")
