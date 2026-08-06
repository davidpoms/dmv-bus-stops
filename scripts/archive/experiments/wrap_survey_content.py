from pathlib import Path

p = Path("src/review/render_survey.py")

text = p.read_text()


start_marker = '''
    # Always include remote-visible questions.
    # In-person review adds additional observations.
    # Steward questions are available to all reviewers.
'''


start = text.find(start_marker)

if start == -1:
    raise Exception(
        "Could not find survey sections start"
    )


end_marker = '''
    html.append(
        render_question(
            SURVEY["notes"]
        )
    )
'''


end = text.find(end_marker, start)

if end == -1:
    raise Exception(
        "Could not find notes block"
    )


sections = text[start:end]


wrapped = '''
    # Always include remote-visible questions.
    # In-person review adds additional observations.
    # Steward questions are available to all reviewers.


    html.append(
        """
        <div id="surveyContent" style="display:none;">
        """
    )


''' + sections.split("\n", 4)[-1] + '''


    html.append(
        """
        </div>
        """
    )

'''


text = (
    text[:start]
    + wrapped
    + text[end:]
)


p.write_text(text)

print(
    "Wrapped survey sections in surveyContent container"
)
