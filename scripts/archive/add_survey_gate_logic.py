from pathlib import Path

p = Path("src/dashboard/static/review_survey.js")

text = p.read_text()


old = """
            const mode = getReviewMode();


            document
            .querySelectorAll(
                ".survey-section"
            )
"""


new = """
            const mode = getReviewMode();


            const survey =
                document.getElementById(
                    "surveyContent"
                );


            if(survey){

                survey.style.display =
                    mode
                    ? "block"
                    : "none";

            }


            document
            .querySelectorAll(
                ".survey-section"
            )
"""


if old not in text:
    raise Exception(
        "Could not find updateSections mode block"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Added survey gate visibility logic"
)
