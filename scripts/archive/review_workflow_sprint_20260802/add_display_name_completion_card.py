from pathlib import Path

path = Path(
    "src/dashboard/templates/review.html"
)

text = path.read_text(
    encoding="utf-8"
)


needle = """
<h1>
Thank you for helping improve bus stops!
</h1>
"""


replacement = """
<h1>
Thank you for helping improve bus stops!
</h1>


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

"""


if needle not in text:
    raise SystemExit(
        "Completion heading not found"
    )


text = text.replace(
    needle,
    replacement,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Added display name to completion card"
)