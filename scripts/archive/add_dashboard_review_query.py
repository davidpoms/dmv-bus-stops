from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


marker = """
let markers = [];
"""


insert = """
let reviewMode = "";

const dashboardParams =
    new URLSearchParams(
        window.location.search
    );


if (dashboardParams.get("review")) {

    reviewMode =
        dashboardParams.get("review");

}

"""


if marker not in text:
    print("marker not found")
    raise SystemExit(1)


text = text.replace(
    marker,
    marker + insert
)


text = text.replace(
"""
    let params = new URLSearchParams();
""",
"""
    let params = new URLSearchParams();


    if (reviewMode) {
        params.append(
            "review",
            reviewMode === "opportunity"
            ? "needed"
            : reviewMode
        );
    }
"""
)


p.write_text(text)

print("dashboard review query wired")
