from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old_start = """
                                    let popup = `
"""

start = text.find(old_start)

if start == -1:
    print("popup start not found")
    raise SystemExit(1)


# Find the first popup close after this section
end_marker = """
                                    `;


                                    if (detail.projects.length > 0) {
"""

end = text.find(end_marker, start)


if end == -1:
    print("popup end marker not found")
    raise SystemExit(1)


old_block = text[start:end + len("                                    `;")]


new_block = """
                                    let popup = `

                                    <b>${props.location}</b><br><br>


                                    <h3>Community Journey</h3>


                                    <b>1. Opportunity Identified</b><br>

                                    Transit improvement opportunity detected.

                                    <br><br>


                                    <b>2. Volunteer Verification</b><br>

                                    Street View reviews:

                                    ${journey.journey.streetview.completed_reviews}

                                    /

                                    ${journey.journey.streetview.required_reviews}

                                    complete

                                    <br>

                                    Status:

                                    ${journey.journey.streetview.status}


                                    <br><br>


                                    <b>3. Field Review</b><br>

                                    Status:

                                    ${journey.journey.field_review.status}


                                    <br><br>


                                    <b>4. Community Action</b><br>

                                    Status:

                                    ${journey.journey.community_project.status}


                                    <br><br>


                                    <b>Opportunity Signal</b><br>

                                    Ridership / impact signal:

                                    ${props.impact}

                                    <br>

                                    Score:

                                    ${props.score}


                                    <br><br>


                                    <b>How you can help</b><br>

                                    Review this stop in Street View and help confirm whether riders need improvement.

                                    `;

"""

text = text.replace(
    old_block,
    new_block
)


p.write_text(text)

print("popup cleanup patched")
