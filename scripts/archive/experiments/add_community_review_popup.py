from pathlib import Path

path = Path("src/dashboard/static/dashboard.js")

text = path.read_text(encoding="utf-8")


needle = """
                                <br><br>

                                <b>WMATA Stop IDs:</b>
"""


insert = """
                                <br><br>

                                ${
                                    detail.community_review &&
                                    detail.community_review.has_reviewed
                                    ?
                                    `
                                    <b>✅ You have reviewed this stop</b><br>
                                    Community observations submitted:
                                    ${detail.community_review.review_count}
                                    `
                                    :
                                    `
                                    <b>Community review status:</b><br>
                                    No review submitted by you yet.
                                    `
                                }


                                <br><br>

                                <b>WMATA Stop IDs:</b>
"""


if needle not in text:
    raise Exception(
        "Could not find insertion point"
    )


text = text.replace(
    needle,
    insert,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Added community review status to dashboard popup"
)