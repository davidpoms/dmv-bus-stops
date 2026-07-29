from pathlib import Path

p = Path("src/dashboard/static/review_stop.js")

text = p.read_text()


old = """
        const formData =
            new FormData(form);


        const data =
            Object.fromEntries(
                formData.entries()
            );
"""


new = """
        const formData =
            new FormData(form);


        const data = {};


        for (const [key, value] of formData.entries()) {

            if (data[key]) {

                if (!Array.isArray(data[key])) {
                    data[key] = [
                        data[key]
                    ];
                }

                data[key].push(value);

            }

            else {

                data[key] = value;

            }

        }
"""


if old not in text:
    raise Exception(
        "Could not find FormData conversion block"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Added checkbox array submission support"
)
