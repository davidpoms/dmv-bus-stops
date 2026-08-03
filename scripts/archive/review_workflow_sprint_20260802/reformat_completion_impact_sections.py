from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")


start_marker = """
<p>
You have completed
<strong>${result.reviewer_stats.review_count}</strong>
review(s).
</p>
"""


end_marker = """
${
    result.community_impact.routes &&
    result.community_impact.routes.length
    ?
    `
    <p>
    Route(s) reviewed:
    <strong>
    ${result.community_impact.routes.join(", ")}
    </strong>
    </p>
    `
    :
    ""
}
"""


start = text.find(start_marker)

if start == -1:
    raise Exception("start marker not found")


end = text.find(end_marker, start)

if end == -1:
    raise Exception("end marker not found")


end += len(end_marker)


replacement = """
<div class="impact-section">

<h2>
Your community contribution
</h2>


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
    Your completed reviews represent approximately
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

</div>


<div class="impact-section current-review">

<h2>
This review
</h2>


<p>
Your review helped validate a stop serving approximately
<strong>
${
    result.community_impact.daily_route_exposure
    ?
    Math.round(
        result.community_impact.daily_route_exposure
    ).toLocaleString()
    :
    "unknown"
}
</strong>
weekday riders.
</p>


${
    result.community_impact.routes &&
    result.community_impact.routes.length
    ?
    `
    <p>
    Routes served:
    <strong>
    ${result.community_impact.routes.join(", ")}
    </strong>
    </p>
    `
    :
    ""
}


${
    result.reviewer_stats.first_review
    ?
    `
    <p>
    ⭐ You established the first community record for this stop.
    </p>
    `
    :
    ""
}

</div>
"""


text = text[:start] + replacement + text[end:]


path.write_text(
    text,
    encoding="utf-8"
)

print("Reformatted completion impact sections")