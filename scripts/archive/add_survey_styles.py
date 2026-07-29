from pathlib import Path

p = Path("src/dashboard/static/dashboard.css")

text = p.read_text()


addition = """



/* Community review survey */


.survey-intro {

    background: #f5f7f9;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 25px;

}


.survey-intro h2 {

    margin-top: 0;

}


.survey-intro p {

    line-height: 1.5;

}



.survey-section {

    margin-bottom: 30px;

}



.survey-question {

    margin-bottom: 24px;
    padding: 20px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 10px;

}



.survey-question > label {

    display: block;
    font-weight: 600;
    font-size: 16px;
    margin-bottom: 12px;

}



.survey-question select,
.survey-question textarea,
.survey-question input[type="text"],
.survey-question input[type="email"] {

    width: 100%;
    box-sizing: border-box;
    padding: 12px;
    font-size: 16px;
    border-radius: 6px;
    border: 1px solid #bbb;

}



.survey-question textarea {

    min-height: 120px;
    resize: vertical;

}



.survey-question input[type="radio"] {

    margin-right: 8px;

}



.survey-question label:has(input[type="radio"]) {

    font-weight: normal;
    margin-bottom: 10px;

}


"""


if "/* Community review survey */" not in text:

    text += addition


p.write_text(text)

print(
    "Added survey styling"
)
