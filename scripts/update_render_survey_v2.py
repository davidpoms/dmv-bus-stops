from pathlib import Path

path = Path("src/review/render_survey.py")

text = path.read_text()

text = text.replace(
'''    html.append(
        f"""
        <div class="survey-question"
             data-field="{field}">
        <label>
        {escape(label)}
        </label>
        """
    )
''',
'''    condition = question.get("condition", "")
    always_visible = question.get("always_visible", False)
    required_when = question.get("required_when", [])

    html.append(
        f"""
        <div class="survey-question"
             data-field="{field}"
             data-condition="{escape(condition)}"
             data-always-visible="{str(always_visible).lower()}"
             data-required-when="{escape(",".join(required_when))}">
        <label>
        {escape(label)}
        </label>
        """
    )
'''
)

text = text.replace(
'''    elif qtype == "textarea":

        html.append(
            f"""
            <textarea
                name="{field}">
            </textarea>
            """
        )
''',
'''    elif qtype == "textarea":

        html.append(
            f"""
            <textarea
                name="{field}">
            </textarea>
            """
        )


    elif qtype == "text":

        html.append(
            f"""
            <input
                type="text"
                name="{field}">
            """
        )


    elif qtype == "multiselect":

        html.append(
            f"""
            <select
                name="{field}"
                multiple>
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
'''
)

text = text.replace(
'''        <section
        class="survey-section"
        data-section="{section_name}">
''',
'''        <section
        class="survey-section"
        data-section="{section_name}"
        data-review-mode="{section_name}">
'''
)

path.write_text(text)

print("Updated render_survey.py")
