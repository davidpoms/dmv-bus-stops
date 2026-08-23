from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")


needle = """
<p>
Your review has been recorded.
</p>
"""

replacement = """
<p>
Your review has been recorded.
</p>

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
    raise SystemExit("completion message not found")


text=text.replace(
    needle,
    replacement,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)

print("Added welcome message")