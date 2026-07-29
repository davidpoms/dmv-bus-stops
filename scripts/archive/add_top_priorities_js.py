from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

insert = """

function loadTopPriorities(){

    fetch("/priorities/top")

    .then(
        response => response.json()
    )

    .then(
        data => {

            let html = "";

            data.forEach(
                item => {

                    html += `
                    <div class="priorityItem">
                    <b>${item.location}</b><br>
                    Score: ${item.score}<br>
                    Priority: ${item.priority}<br>
                    Impact: ${item.impact}
                    <hr>
                    </div>
                    `;

                }
            );

            document
            .getElementById("topPriorityList")
            .innerHTML = html;

        }
    );

}


loadTopPriorities();

"""

marker = "loadStops();"

if marker in text:
    text = text.replace(marker, insert + "\n" + marker, 1)
    p.write_text(text)
    print("Added top priorities loader")
else:
    print("loadStops marker not found")
