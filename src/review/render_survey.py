"""
Render community survey questions into HTML.

Uses community_survey_v1.py as the source of truth.
"""

from html import escape

from .community_survey_v1 import SURVEY


def render_options(options):
    html = []

    for value, label in options:
        html.append(
            f"""
            <option value="{escape(value)}">
                {escape(label)}
            </option>
            """
        )

    return "\n".join(html)



def render_question(question):

    field = question["field"]
    label = question["label"]

    qtype = question.get(
        "type",
        "select"
    )

    multiple = question.get(
        "multiple",
        False
    )

    condition = question.get(
        "condition",
        ""
    )

    html = []

    html.append(
        f"""
        <div class="survey-question"
             data-field="{escape(field)}"
             data-condition="{escape(condition)}">

        <label>
        {escape(label)}
        </label>
        """
    )


    if qtype == "radio":

        for value, label in question.get("options", []):

            html.append(
                f"""
                <label>
                <input
                    type="radio"
                    name="{escape(field)}"
                    value="{escape(value)}">
                {escape(label)}
                </label>
                """
            )


    elif multiple:

        for value, label in question.get("options", []):

            html.append(
                f"""
                <label class="checkbox-option">
                <input
                    type="checkbox"
                    name="{escape(field)}[]"
                    value="{escape(value)}">
                {escape(label)}
                </label>
                """
            )


    elif qtype == "select":

        html.append(
            f"""
            <select name="{escape(field)}">
            """
        )

        for value, label in question.get("options", []):

            html.append(
                f"""
                <option value="{escape(value)}">
                {escape(label)}
                </option>
                """
            )

        html.append(
            "</select>"
        )


    elif qtype == "textarea":

        html.append(
            f"""
            <textarea
                name="{escape(field)}">
            </textarea>
            """
        )


    elif qtype == "month":

        html.append(
            f"""
            <input
                type="month"
                name="{escape(field)}">
            """
        )


    elif qtype == "text":

        html.append(
            f"""
            <input
                type="text"
                name="{escape(field)}">
            """
        )

    return "\n".join(html)



def render_section(section_name):

    html = []

    html.append(
        f"""
        <section
        class="survey-section"
        data-section="{section_name}"
        data-review-mode="{section_name}">
        """
    )


    for question in SURVEY.get(
        section_name,
        []
    ):
        html.append(
            render_question(question)
        )


    html.append(
        "</section>"
    )

    return "\n".join(html)



def render_survey():

    html = []

    html.append(
        render_question(
            {
                "field": "review_mode",
                "label": SURVEY["review_mode"]["label"],
                "type": SURVEY["review_mode"]["type"],
                "options": SURVEY["review_mode"]["options"]
            }
        )
    )


    # Always include remote-visible questions.
    # In-person review adds additional observations.
    # Steward questions are available to all reviewers.


    html.append(
        """
        <div id="surveyContent" style="display:none;">
        """
    )



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




    html.append(
        render_question(
            SURVEY["notes"]
        )
    )

    html.append(
        """
        </div>
        """
    )




    return "\n".join(html)
