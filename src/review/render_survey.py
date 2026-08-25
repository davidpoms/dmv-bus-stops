"""
Render community survey questions into HTML.

Uses community_survey_v1.py as the source of truth.
"""

from html import escape

from .community_survey_v1 import SURVEY


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

    prompt = (
        f"<fieldset><legend>{escape(label)}</legend>"
        if qtype == "radio" or multiple
        else f'<label for="survey-{escape(field)}">{escape(label)}</label>'
    )
    html.append(
        f"""
        <div
            class="survey-question"
            data-field="{escape(field)}"
            data-condition="{escape(condition)}"
        >
            {prompt}
        """
    )

    if qtype == "radio":

        for value, option_label in question.get("options", []):

            html.append(
                f"""
                <label>
                    <input
                        type="radio"
                        name="{escape(field)}"
                        value="{escape(value)}"
                    >
                    {escape(option_label)}
                </label>
                """
            )

    elif multiple:

        for value, option_label in question.get("options", []):

            html.append(
                f"""
                <label class="checkbox-option">
                    <input
                        type="checkbox"
                        name="{escape(field)}[]"
                        value="{escape(value)}"
                    >
                    {escape(option_label)}
                </label>
                """
            )

    elif qtype == "select":

        html.append(
            f"""
            <select id="survey-{escape(field)}" name="{escape(field)}">
            """
        )

        for value, option_label in question.get("options", []):

            html.append(
                f"""
                <option value="{escape(value)}">
                    {escape(option_label)}
                </option>
                """
            )

        html.append(
            """
            </select>
            """
        )

    elif qtype == "textarea":

        html.append(
            f"""
            <textarea
                id="survey-{escape(field)}"
                name="{escape(field)}"
            ></textarea>
            """
        )

    elif qtype == "month":

        html.append(
            f"""
            <input
                id="survey-{escape(field)}"
                type="month"
                name="{escape(field)}"
            >
            """
        )

    elif qtype == "text":

        html.append(
            f"""
            <input
                id="survey-{escape(field)}"
                type="text"
                name="{escape(field)}"
            >
            """
        )

    if qtype == "radio" or multiple:
        html.append("</fieldset>")

    html.append(
        """
        </div>
        """
    )

    return "\n".join(html)


def render_section(section_name):

    html = []

    html.append(
        f"""
        <section
            class="survey-section"
            data-section="{escape(section_name)}"
            data-review-mode="{escape(section_name)}"
        >
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
        """
        </section>
        """
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

    html.append(
        """
        <div
            id="surveyContent"
            style="display:none;"
        >
        """
    )

    html.append(
        """
        <div
            class="survey-group"
            data-review-mode="remote"
        >

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
        <div
            class="survey-group"
            data-review-mode="in_person"
        >

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
        <div
            class="survey-group"
            data-review-mode="steward"
        >

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
