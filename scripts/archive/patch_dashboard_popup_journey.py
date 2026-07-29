from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
                                let popup = `
                                <b>${props.location}</b><br><br>

                                Score: ${props.score}<br>
                                Priority: ${props.priority}<br>
                                Impact: ${props.impact}<br><br>

                                <b>Projects</b><br>
                                `;
"""


new = """
                                fetch(
                                    `/stops/${props.stop_id}/community-status`
                                )
                                .then(
                                    response => response.json()
                                )
                                .then(
                                    journey => {

                                    let popup = `
                                    <b>${props.location}</b><br><br>

                                    <b>Community Journey</b><br><br>

                                    Street View Review:<br>
                                    ${journey.journey.streetview.completed_reviews}
                                    /
                                    ${journey.journey.streetview.required_reviews}
                                    volunteers<br>

                                    Status:
                                    ${journey.journey.streetview.status}
                                    <br><br>

                                    Field Review:<br>
                                    ${journey.journey.field_review.status}
                                    <br><br>

                                    Community Project:<br>
                                    ${journey.journey.community_project.status}
                                    <br><br>

                                    <b>Opportunity Signal</b><br>

                                    Score:
                                    ${props.score}<br>

                                    Impact:
                                    ${props.impact}<br>
                                    `;
"""


if old not in text:
    print("popup block not found")
    raise SystemExit(1)


text = text.replace(
    old,
    new
)


p.write_text(text)

print("dashboard popup journey patched")
