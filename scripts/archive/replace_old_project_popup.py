from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
                                    Community Project:<br>
                                    ${journey.journey.community_project.status}
                                    <br><br>
"""

new = """
                                    <b>Community Action Details</b><br>

                                    ${
                                        journey.journey.community_action.length
                                        ?
                                        journey.journey.community_action[0].status
                                        :
                                        "No action started"
                                    }
                                    <br>

                                    ${
                                        journey.journey.community_action.length
                                        ?
                                        journey.journey.community_action[0].project_type
                                        :
                                        ""
                                    }

                                    <br><br>
"""

if old not in text:
    print("old project popup block not found")
    raise SystemExit(1)

text = text.replace(old, new, 1)

p.write_text(text)

print("old project popup replaced")
