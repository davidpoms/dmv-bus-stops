from pathlib import Path

p = Path("src/review/render_survey.py")

text = p.read_text()


old = '''
    html.append(
        render_section("remote")
    )

    html.append(
        render_section("in_person")
    )

    html.append(
        render_section("steward")
    )
'''


new = '''
    html.append(
        """
        <h2 class="survey-section-title">
        What can be seen from this stop
        </h2>
        """
    )

    html.append(
        render_section("remote")
    )


    html.append(
        """
        <h2 class="survey-section-title">
        Observations from visiting this stop
        </h2>
        """
    )

    html.append(
        render_section("in_person")
    )


    html.append(
        """
        <h2 class="survey-section-title">
        Community involvement
        </h2>
        """
    )

    html.append(
        render_section("steward")
    )
'''


if old not in text:
    raise Exception(
        "Could not find survey section rendering block"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Added survey section headers"
)
