from pathlib import Path

p = Path("src/dashboard/templates/review.html")

text = p.read_text()


old = """
let form =
new FormData(e.target);


let payload =
Object.fromEntries(form.entries());
"""


new = """
let form =
new FormData(e.target);


let payload = {};


for (const [key, value] of form.entries()) {

    const cleanKey =
        key.endsWith("[]")
        ? key.slice(0, -2)
        : key;


    if (payload[cleanKey]) {

        if (!Array.isArray(payload[cleanKey])) {

            payload[cleanKey] =
                [
                    payload[cleanKey]
                ];

        }


        payload[cleanKey].push(value);

    }

    else {

        payload[cleanKey] =
            value;

    }

}
"""


if old not in text:
    raise Exception(
        "Could not find review form payload block"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Updated review form to preserve multi-select values"
)
