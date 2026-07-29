from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

kpi_block = """
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

# Remove KPI block wherever it currently exists
if kpi_block in text:
    text = text.replace(kpi_block, "")

# Insert before routes fetch
marker = """
fetch("/routes")
"""

if marker not in text:
    raise SystemExit("Could not find fetch('/routes') marker")

text = text.replace(
    marker,
    kpi_block + marker,
    1
)

p.write_text(text)

print("fixed KPI placement")
