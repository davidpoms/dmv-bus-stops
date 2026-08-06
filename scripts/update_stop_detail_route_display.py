from pathlib import Path


path = Path("src/dashboard/static/stop_detail.js")

text = path.read_text(encoding="utf-8")


old = """
        const routes =
            stop.routes ||
            review.routes ||
            review.ridership_exposure?.routes ||
            [];

        const routeText =
            Array.isArray(routes)
            ? routes.join(", ")
            : routes || "No route data";
"""


new = """
        const routeIds =
            stop.impact_summary?.routes ||
            review.impact_summary?.routes ||
            review.ridership_exposure?.routes ||
            [];


        const routeNames =
            stop.routes ||
            review.routes ||
            [];


        let routeText = "No route data";


        if (
            Array.isArray(routeIds) &&
            Array.isArray(routeNames)
        ) {

            const combined = [];


            const count =
                Math.max(
                    routeIds.length,
                    routeNames.length
                );


            for (
                let i = 0;
                i < count;
                i++
            ) {

                const id =
                    routeIds[i] || "";

                const name =
                    routeNames[i] || "";


                if (id && name) {

                    combined.push(
                        `${id} — ${name}`
                    );

                }

                else if (id) {

                    combined.push(id);

                }

                else if (name) {

                    combined.push(name);

                }

            }


            routeText =
                combined.join("<br>");

        }

        else if (Array.isArray(routeNames)) {

            routeText =
                routeNames.join("<br>");

        }
"""


if old not in text:
    raise Exception(
        "Could not find current route block"
    )


text = text.replace(
    old,
    new,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Updated stop detail route display"
)