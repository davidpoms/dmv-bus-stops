from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
            status.innerText =
                "Showing: "
"""


new = """
            let modeText = "";

            if (reviewMode === "opportunity") {

                modeText =
                    "Volunteer review queue: highest opportunities awaiting validation | ";

            }

            else if (reviewMode === "route") {

                modeText =
                    "Route stewardship review | ";

            }

            else if (reviewMode === "nearby") {

                modeText =
                    "Nearby volunteer review | ";

            }


            status.innerText =
                modeText
                +
                "Showing: "
"""


if old not in text:
    print("status marker not found")
    raise SystemExit(1)


text = text.replace(old,new)


p.write_text(text)

print("review mode status patched")
