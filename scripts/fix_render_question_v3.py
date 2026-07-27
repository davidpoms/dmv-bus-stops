from pathlib import Path

path = Path("src/review/render_survey.py")

text = path.read_text()

start = text.index("def render_question(")
end = text.index("\n\ndef render_section")

new = r'''
def render_question(question):

    field = question["field"]
    label = question["label"]

    qtype = question.get(
        "type",
        "select"
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


    elif qtype == "text":

        html.append(
            f"""
            <input
                type="text"
                name="{escape(field)}">
            """
        )


    html.append(
        "</div>"
    )

    return "\n".join(html)

'''

text = text[:start] + new + text[end:]

path.write_text(text)

print("Updated render_question")
