from pathlib import Path


STOP_JS = Path(
    "src/dashboard/static/stop_detail.js"
)

REVIEW_JS = Path(
    "src/dashboard/static/review_info_loader.js"
)


def replace_section(path, start, end, replacement):

    text = path.read_text(
        encoding="utf-8"
    )

    s = text.find(start)

    if s == -1:
        raise Exception(
            f"Could not find start marker in {path}: {start}"
        )

    e = text.find(end, s)

    if e == -1:
        raise Exception(
            f"Could not find end marker in {path}: {end}"
        )

    text = (
        text[:s]
        + replacement
        + text[e:]
    )

    path.write_text(
        text,
        encoding="utf-8"
    )


# -------------------------------------------------
# Stop detail: rename Evidence heading only
# -------------------------------------------------

stop_text = STOP_JS.read_text(
    encoding="utf-8"
)

stop_text = stop_text.replace(
    "Evidence & Data Sources",
    "Evidence sources"
)

STOP_JS.write_text(
    stop_text,
    encoding="utf-8"
)


# -------------------------------------------------
# Review page: rename priority card language
# -------------------------------------------------

review_text = REVIEW_JS.read_text(
    encoding="utf-8"
)

review_text = review_text.replace(
    "Why this stop was prioritized",
    "Why this stop was selected"
)

review_text = review_text.replace(
    "Why this stop needs verification",
    "Community verification need"
)

REVIEW_JS.write_text(
    review_text,
    encoding="utf-8"
)


print(
    "Aligned stop and review card terminology"
)