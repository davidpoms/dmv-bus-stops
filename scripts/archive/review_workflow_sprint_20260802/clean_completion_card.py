from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")


welcome_block = '''
${
    result.reviewer_stats.display_name
    ?
    `
    <p>
    Welcome back,
    <strong>
    ${result.reviewer_stats.display_name}
    </strong>
    !
    </p>
    `
    :
    ""
}
'''


first = text.find(welcome_block)
second = text.find(welcome_block, first + 1)


if first != -1 and second != -1:

    text = (
        text[:second]
        +
        text[second + len(welcome_block):]
    )

    print("Removed duplicate welcome message")

else:
    print("Duplicate welcome block not found")


impact_marker = '''
<p>
You have completed
<strong>${result.reviewer_stats.review_count}</strong>
review(s).
</p>
'''


routes_block = '''
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
'''


if routes_block not in text:

    text = text.replace(
        impact_marker,
        impact_marker + "\n" + routes_block
    )

    print("Added routes display")

else:
    print("Routes display already exists")


path.write_text(
    text,
    encoding="utf-8"
)