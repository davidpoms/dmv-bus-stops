from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
if (dashboardParams.get("review")) {

    reviewMode =
        dashboardParams.get("review");

}

"""

new = """
if (dashboardParams.get("review")) {

    reviewMode =
        dashboardParams.get("review");

}


if (dashboardParams.get("action")) {

    actionFilter =
        dashboardParams.get("action");

}

"""

if old not in text:
    print("url anchor not found")
    raise SystemExit(1)

text=text.replace(old,new,1)

p.write_text(text)

print("action url reader added")
