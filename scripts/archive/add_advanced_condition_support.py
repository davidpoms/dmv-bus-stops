from pathlib import Path

p = Path("src/dashboard/static/review_survey.js")

text = p.read_text()


start = text.find(
    "function evaluateCondition(condition){"
)

end = text.find(
    "function updateQuestionVisibility()",
    start
)

if start == -1 or end == -1:
    raise Exception(
        "Could not find condition functions"
    )


new_function = """
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


"""


text = (
    text[:start]
    + new_function
    + text[end:]
)


p.write_text(text)

print(
    "Added advanced condition operators"
)
