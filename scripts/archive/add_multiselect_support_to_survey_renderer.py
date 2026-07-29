from pathlib import Path

p = Path("src/review/render_survey.py")

text = p.read_text()


old = '''
    qtype = question.get(
        "type",
        "select"
    )

    condition = question.get(
        "condition",
        ""
    )
'''


new = '''
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
'''


if old not in text:
    raise Exception(
        "Could not find question type block"
    )


text = text.replace(
    old,
    new
)


old = '''
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
'''


new = '''
    elif multiple:

        for value, label in question.get("options", []):

            html.append(
                f"""
                <label class="checkbox-option">
                <input
                    type="checkbox"
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
'''


if old not in text:
    raise Exception(
        "Could not find select renderer block"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Added multi-select checkbox support"
)
