from pathlib import Path


# -----------------------------
# Fix dashboard CSS layout
# -----------------------------

css = Path(
    "src/dashboard/static/dashboard.css"
)

text = css.read_text(
    encoding="utf-8"
)


if ".map-filter-grid" not in text:

    text += """

/* Map filter layout */

.map-filter-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 20px;
    align-items: end;
}

.map-filter-card label {
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
}

.map-filter-card select {
    width: 100%;
    min-height: 42px;
}

.route-filter-card,
.geo-filter-card {
    margin-bottom: 20px;
}

"""

else:

    text = text.replace(
        "gap: 10px;",
        "gap: 20px;",
        1
    )


css.write_text(
    text,
    encoding="utf-8"
)


# -----------------------------
# Fix map marker styling
# -----------------------------

js = Path(
    "src/dashboard/static/dashboard.js"
)

text = js.read_text(
    encoding="utf-8"
)


old = """
let color =
    props.impact === "very_high"
    ? "red"
    : props.impact === "high"
    ? "orange"
    : "gray";
"""


new = """
let color = "#3388ff";
"""


if old in text:
    text = text.replace(
        old,
        new
    )


# Catch alternate marker sizing patterns

text = text.replace(
    """
radius:
    props.impact === "very_high"
    ? 10
    : props.impact === "high"
    ? 8
    : 6
""",
    """
radius: 7
"""
)


text = text.replace(
    """
radius:
    props.priority === "very_high"
    ? 10
    : props.priority === "high"
    ? 8
    : 6
""",
    """
radius: 7
"""
)


js.write_text(
    text,
    encoding="utf-8"
)


print(
    "Filter layout spacing and marker styling updated."
)