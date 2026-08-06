from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")


anchor = """
    </p>
    `
    :
    ""
}
"""


insert = """
    </p>
    `
    :
    ""
}

<p class="impact-note">
Ridership figures represent route-level weekday boardings associated with
routes serving reviewed stops. They do not represent unique riders or
stop-level boardings.
</p>
"""


if "Ridership figures represent route-level weekday boardings" in text:
    print("Disclaimer already exists")
    raise SystemExit


if anchor not in text:
    raise Exception("Could not find impact block ending")


text = text.replace(
    anchor,
    insert,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)

print("Added ridership clarification")