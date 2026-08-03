from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")


needle = """
<p>
You have completed
<strong>${result.reviewer_stats.review_count}</strong>
review(s).
</p>
"""


replacement = """
<p>
You have completed
<strong>${result.reviewer_stats.review_count}</strong>
review(s).
</p>


${
    result.reviewer_stats.stops_reviewed
    ?
    `
    <p>
    You have helped validate
    <strong>
    ${result.reviewer_stats.stops_reviewed}
    </strong>
    unique stop(s).
    </p>
    `
    :
    ""
}


${
    result.reviewer_stats.total_rider_impact
    ?
    `
    <p>
    Your reviews have helped validate stops serving approximately
    <strong>
    ${result.reviewer_stats.total_rider_impact.toLocaleString()}
    </strong>
    weekday riders.
    </p>
    `
    :
    ""
}


${
    result.reviewer_stats.routes_covered &&
    result.reviewer_stats.routes_covered.length
    ?
    `
    <p>
    Routes covered:
    <strong>
    ${result.reviewer_stats.routes_covered.join(", ")}
    </strong>
    </p>
    `
    :
    ""
}
"""


if needle not in text:
    raise Exception("completion review count block not found")


text = text.replace(
    needle,
    replacement,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)

print("Added completion profile stats")