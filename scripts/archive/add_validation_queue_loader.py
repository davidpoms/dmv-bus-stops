from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

if "function loadValidationQueue" not in text:

    insert = r'''

function loadValidationQueue(){

    fetch("/validation/queue")

    .then(response => response.json())

    .then(data => {

        const box =
            document.getElementById("validationList");

        if (!box) {
            return;
        }

        box.innerHTML = "";

        data.slice(0,10).forEach(stop => {

            box.innerHTML += `

            <div class="priorityItem"
                 onclick="window.location='/survey-page/${stop.stop_id}'"
                 style="cursor:pointer;">

                <b>${stop.priority}</b>
                ${stop.location}

                <br>

                Score: ${stop.score}

                <br>

                Status:
                ${stop.status}

                <br><br>

                <a href="${stop.streetview_url}"
                   target="_blank"
                   onclick="event.stopPropagation();">
                   Open Street View
                </a>

            </div>

            `;

        });

    });

}

'''

    # put it before the final DOM close
    pos = text.rfind("\n});")

    text = text[:pos] + insert + text[pos:]

    p.write_text(text)

    print("Added validation queue loader")

else:
    print("Validation queue loader already exists")
