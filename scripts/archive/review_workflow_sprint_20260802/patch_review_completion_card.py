from pathlib import Path

html = Path("src/dashboard/templates/review.html")

text = html.read_text(encoding="utf-8")


old = """
<p>
You have completed
<strong>${result.review_count}</strong>
review(s).
</p>
"""


new = """
<p>
You have completed
<strong>${result.reviewer_stats.review_count}</strong>
review(s).
</p>

<p>
This stop serves approximately
<strong>
${
    result.community_impact.daily_route_exposure
    ? result.community_impact.daily_route_exposure.toLocaleString()
    : "unknown"
}
</strong>
daily riders through the routes serving it.
</p>

${
    result.reviewer_stats.first_review
    ?
    `
    <p>
    ⭐ You were the first community reviewer for this stop.
    </p>
    `
    :
    ""
}
"""


if old not in text:
    raise RuntimeError(
        "Could not find completion review count block"
    )


text = text.replace(old, new)

html.write_text(text, encoding="utf-8")

print("Updated volunteer impact completion card.")