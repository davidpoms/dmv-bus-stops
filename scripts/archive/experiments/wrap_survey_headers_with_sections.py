from pathlib import Path

p = Path("src/review/render_survey.py")

text = p.read_text()


old = '''
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


new = '''
    html.append(
        """
        <div class="survey-group" data-review-mode="remote">
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
        </div>
        """
    )


    html.append(
        """
        <div class="survey-group" data-review-mode="in_person">
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
        </div>
        """
    )


    html.append(
        """
        <div class="survey-group" data-review-mode="steward">
        <h2 class="survey-section-title">
        Community involvement
        </h2>
        """
    )

    html.append(
        render_section("steward")
    )

    html.append(
        """
        </div>
        """
    )
'''


if old not in text:
    raise Exception(
        "Could not find survey header blocks"
    )


text = text.replace(old, new)

p.write_text(text)

print("Wrapped survey headers with sections")
