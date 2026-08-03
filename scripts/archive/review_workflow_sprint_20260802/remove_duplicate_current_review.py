from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")


duplicate = """
<p>
This stop is served by routes representing approximately
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
weekday boardings.
</p>


${
    result.community_impact.routes &&
    result.community_impact.routes.length
    ?
    `
    <p>
    Route(s):
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
"""


if duplicate not in text:
    raise Exception("Duplicate current review block not found")


text = text.replace(
    duplicate,
    "",
    1
)


path.write_text(
    text,
    encoding="utf-8"
)

print("Removed duplicate current review block")