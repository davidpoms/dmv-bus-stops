from pathlib import Path


# ----------------------------
# Fix dashboard CSS
# ----------------------------

css_path = Path(
    "src/dashboard/static/dashboard.css"
)

css = css_path.read_text(
    encoding="utf-8"
)


css_append = """

/* Final map filter cleanup */

.map-filter-card .filter-row {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    align-items: flex-end;
}


.map-filter-card .filter-group,
.map-filter-card label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 160px;
}


.map-filter-card select {
    width: 180px;
    height: 40px;
}


.map-filter-card button {
    height: 40px;
    margin-bottom: 0;
}

"""


if "Final map filter cleanup" not in css:
    css += css_append


css_path.write_text(
    css,
    encoding="utf-8"
)


# ----------------------------
# Fix dashboard JS markers
# ----------------------------

js_path = Path(
    "src/dashboard/static/dashboard.js"
)

js = js_path.read_text(
    encoding="utf-8"
)


old = """
                let color = "gray";
                let radius = 5;


                if (
                    props.impact === "very_high"
                ) {
                    color = "red";
                    radius = 14;
                }

                else if (
                    props.impact === "high"
                ) {
                    color = "orange";
                    radius = 10;
                }

                else if (
                    props.impact === "medium"
                ) {
                    color = "gold";
                    radius = 7;
                }
"""


new = """
                let color = "gray";
                let radius = 7;
"""


if old not in js:
    raise Exception(
        "Could not find marker styling block"
    )


js = js.replace(
    old,
    new
)


old2 = """
                            pane:
                                props.impact === "very_high"
                                ? "veryHighPriority"
                                :
                                props.impact === "high"
                                ? "highPriority"
                                :
                                "markerPane"
"""


new2 = """
                            pane: "markerPane"
"""


if old2 in js:
    js = js.replace(
        old2,
        new2
    )


js_path.write_text(
    js,
    encoding="utf-8"
)


print(
    "Filter layout and marker cleanup complete."
)