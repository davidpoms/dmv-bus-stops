from pathlib import Path

p = Path("src/review/render_survey.py")

text = p.read_text()


old = """
def render_survey():

    html = []

    html.append(
        render_question(
"""

new = """
def render_survey():

    html = []

    html.append(
        """
        <div class="survey-intro">

        <h2>
        Help improve this bus stop
        </h2>

        <p>
        Your observations help identify where riders may benefit
        from safer, more comfortable waiting areas. You do not need
        to be an expert — firsthand observations are valuable.
        </p>

        </div>
        """
    )


    html.append(
        render_question(
"""


if old not in text:
    raise Exception(
        "Could not find render_survey start"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Added survey introduction"
)
