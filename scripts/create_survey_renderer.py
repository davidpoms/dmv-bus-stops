from pathlib import Path

path = Path("src/review/render_survey.py")

content = r'''
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
    qtype = question["type"]

    html = []

    html.append(
        f"""
        <div class="survey-question"
             data-field="{field}">
        <label>
        {escape(label)}
        </label>
        """
    )

    if qtype == "radio":

        for value, label in question["options"]:
            html.append(
                f"""
                <label>
                <input
                    type="radio"
                    name="{field}"
                    value="{escape(value)}">
                {escape(label)}
                </label>
                """
            )


    elif qtype == "select":

        html.append(
            f"""
            <select name="{field}">
            """
        )

        html.append(
            render_options(
                question["options"]
            )
        )

        html.append(
            "</select>"
        )


    elif qtype == "textarea":

        html.append(
            f"""
            <textarea
                name="{field}">
            </textarea>
            """
        )


    html.append(
        "</div>"
    )

    return "\n".join(html)



def render_section(section_name):

    html = []

    html.append(
        f"""
        <section
        class="survey-section"
        data-section="{section_name}">
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

    for section in SURVEY:
        html.append(
            render_section(section)
        )

    return "\n".join(html)
'''

path.write_text(content.strip())

print("Created src/review/render_survey.py")
