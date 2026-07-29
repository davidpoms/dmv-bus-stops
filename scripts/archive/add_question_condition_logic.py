from pathlib import Path

p = Path("src/dashboard/static/review_survey.js")

text = p.read_text()


marker = """
        updateSections();

    }
);
"""


replacement = """
        function evaluateCondition(condition){

            const parts =
                condition.split("=");

            const field =
                parts[0];

            const expected =
                parts[1];


            const checked =
                document.querySelectorAll(
                    `[name="${field}[]"]:checked`
                );


            if(checked.length){

                return Array.from(checked)
                    .some(
                        input =>
                            input.value === expected
                    );

            }


            const radio =
                document.querySelector(
                    `[name="${field}"]:checked`
                );


            if(radio){

                return radio.value === expected;

            }


            const select =
                document.querySelector(
                    `[name="${field}"]`
                );


            if(select){

                return select.value === expected;

            }


            return false;

        }



        function updateQuestionVisibility(){

            document
            .querySelectorAll(
                ".survey-question"
            )
            .forEach(question => {

                const condition =
                    question.dataset.condition;


                if(!condition){

                    return;

                }


                question.style.display =
                    evaluateCondition(condition)
                    ? "block"
                    : "none";

            });

        }



        document
        .querySelectorAll(
            "input, select"
        )
        .forEach(control => {

            control.addEventListener(
                "change",
                updateQuestionVisibility
            );

        });



        updateQuestionVisibility();



        updateSections();

    }
);
"""


if marker not in text:
    raise Exception(
        "Could not find updateSections end"
    )


text = text.replace(
    marker,
    replacement
)


p.write_text(text)

print(
    "Added question-level condition logic"
)
