from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

if "communityKPI" in text:
    print("KPI panel already exists")
    raise SystemExit(0)


anchor = "fetch("

insert = """
fetch(
    "/community-actions/summary"
)
.then(
    response => response.json()
)
.then(
    summary => {

        const panel =
            document.createElement("div");


        panel.className =
            "communityKPI";


        panel.innerHTML = `
            <b>Community Actions</b><br><br>

            Planned:
            ${summary.planned}<br>

            In Progress:
            ${summary.in_progress}<br>

            Installed:
            ${summary.installed}<br>

            Total:
            ${summary.total}
        `;


        document.body.appendChild(panel);

    }
);


"""


if anchor not in text:
    print("no fetch anchor found")
    raise SystemExit(1)


text = text.replace(
    anchor,
    insert + anchor,
    1
)

p.write_text(text)

print("community KPI panel added")
