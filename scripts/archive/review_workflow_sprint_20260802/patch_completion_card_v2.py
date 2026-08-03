from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")


start = text.find(
    '<p>\nThis stop serves approximately'
)

end = text.find(
    '<div class="completion-actions">'
)


if start == -1:
    raise RuntimeError(
        "Could not find rider impact section"
    )

if end == -1:
    raise RuntimeError(
        "Could not find completion actions section"
    )


replacement = '''
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


'''


text = (
    text[:start]
    + replacement
    + text[end:]
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Updated volunteer completion card."
)