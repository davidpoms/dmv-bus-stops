from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

marker = "loadStops();"

insert = r'''
function loadPrioritySummary() {

    fetch("/priority-summary")

    .then(response => response.json())

    .then(data => {

        document.getElementById("prioritySummary").innerHTML = `

            <h3>Investment Priorities</h3>

            <div>
            <span class="p1">●</span>
            P1 Immediate: ${data.P1}
            </div>

            <div>
            <span class="p2">●</span>
            P2 High Value: ${data.P2}
            </div>

            <div>
            <span class="p3">●</span>
            P3 Candidate: ${data.P3}
            </div>

            <div>
            Monitor: ${data.monitor}
            </div>

        `;

    });

}


loadPrioritySummary();


'''

if marker in text:
    text = text.replace(marker, insert + marker, 1)
    p.write_text(text)
    print("Added priority summary loader")
else:
    print("loadStops marker not found")
