from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")


# Fix profile language
text = text.replace(
    """Your completed reviews represent approximately
    <strong>
    ${result.reviewer_stats.total_route_boardings_represented.toLocaleString()}
    </strong>
    weekday boardings are represented.""",
    """Your completed reviews are associated with routes representing approximately
    <strong>
    ${result.reviewer_stats.total_route_boardings_represented.toLocaleString()}
    </strong>
    weekday boardings."""
)


# Fix current review language
text = text.replace(
    """Your review helped validate a stop served by routes representing approximately
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
weekday boardings are represented.""",
    """This stop is served by routes representing approximately
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
weekday boardings."""
)


profile_start = text.find('<div class="impact-section">')
review_start = text.find('<div class="impact-section current-review">')

if profile_start == -1 or review_start == -1:
    raise Exception("Could not find impact sections")


if review_start < profile_start:
    print("Sections already reordered")
else:

    # find end of profile section
    profile_end = text.find("</div>\n\n\n<div class=\"impact-section current-review\">")

    if profile_end == -1:
        raise Exception("Could not find profile section end")

    profile_block = text[profile_start:profile_end+6]

    review_end = text.find("</div>", review_start)

    if review_end == -1:
        raise Exception("Could not find review section end")

    review_block = text[review_start:review_end+6]


    text = (
        text[:profile_start]
        + review_block
        + "\n\n\n"
        + profile_block
        + text[review_end+6:]
    )


path.write_text(text, encoding="utf-8")

print("Reordered completion impact sections")