document.addEventListener(
    "DOMContentLoaded",
    () => {


        function getReviewMode(){

            const radio =
                document.querySelector(
                    'input[name="review_mode"]:checked'
                );

            if(radio){
                return radio.value;
            }


            const select =
                document.querySelector(
                    'select[name="review_mode"]'
                );

            if(select){
                return select.value;
            }


            return "";
        }



        function updateSections(){

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
                ".survey-group"
            )
            .forEach(section => {

                const sectionMode =
                    section.dataset.reviewMode;


                if(sectionMode === "remote"){

                    // Remote questions are baseline.
                    // Always show them.
                    section.style.display =
                        "block";

                }


                else if(sectionMode === "in_person"){

                    // Extra observations only.
                    section.style.display =
                        mode === "in_person"
                        ? "block"
                        : "none";

                }


                else if(sectionMode === "steward"){

                    // Steward questions always available.
                    section.style.display =
                        "block";

                }

            });

        }



        document
        .querySelectorAll(
            'input[name="review_mode"], select[name="review_mode"]'
        )
        .forEach(control => {

            control.addEventListener(
                "change",
                updateSections
            );

        });


        
function evaluateCondition(condition){

    let operator = null;
    let field = null;
    let expected = null;


    if(condition.includes(" contains ")){

        [field, expected] =
            condition.split(" contains ");

        operator = "contains";

    }

    else if(condition.includes("!=")){

        [field, expected] =
            condition.split("!=");

        operator = "!=";

    }

    else if(condition.includes("=")){

        [field, expected] =
            condition.split("=");

        operator = "=";

    }


    if(!field){
        return true;
    }


    const values = [];


    document
    .querySelectorAll(
        `[name="${field}[]"]:checked`
    )
    .forEach(input => {

        values.push(input.value);

    });


    const single =
        document.querySelector(
            `[name="${field}"]:checked`
        );


    if(single){
        values.push(single.value);
    }


    const select =
        document.querySelector(
            `[name="${field}"]`
        );


    if(select){
        values.push(select.value);
    }



    if(operator === "contains"){

        return values.includes(expected);

    }


    if(operator === "!="){

        return !values.includes(expected);

    }


    if(operator === "="){

        return values.includes(expected);

    }


    return true;

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


async function loadReviewStopInfo(){

    const parts =
        window.location.pathname.split("/");

    const stopId =
        parts[parts.length - 1];

    if(!stopId){
        return;
    }


    try {

        const response =
            await fetch(
                `/review/${stopId}/info`
            );


        const info =
            await response.json();


        const container = null;


        if(!container){
            return;
        }


        let geography = "";


        if(info.state === "DC"){

            geography =
                `
                DC
                ${info.ward ? " | Ward " + info.ward : ""}
                ${info.anc ? " | ANC " + info.anc : ""}
                `;

        } else {

            geography =
                `
                ${info.state || ""}
                ${info.county ? " | " + info.county : ""}
                ${info.municipality ? " | " + info.municipality : ""}
                `;

        }


        // stopInfo rendering moved to review_info_loader.js


    } catch(err){

        console.error(
            "Could not load stop info",
            err
        );

    }

}


document.addEventListener(
    "DOMContentLoaded",
    loadReviewStopInfo
);

