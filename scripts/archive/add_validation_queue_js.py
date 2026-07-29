from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

marker = """
loadStops();
"""

insert = """
function loadValidationQueue() {

    fetch("/validation/queue")

    .then(
        response => response.json()
    )

    .then(
        data => {

            const list =
                document.getElementById("validationList");


            if (!list) {
                return;
            }


            list.innerHTML = "";


            data.slice(0,10).forEach(
                stop => {

                    list.innerHTML += `

                    <div class="validationItem">

                    <b>${stop.location}</b><br>

                    Priority:
                    ${stop.priority}

                    <br>

                    Score:
                    ${stop.score}

                    <br>

                    Status:
                    ${stop.status}

                    <br><br>

                    <button onclick="validateStop(${stop.stop_id}, 'validated')">
                    Confirm
                    </button>

                    <button onclick="validateStop(${stop.stop_id}, 'rejected')">
                    Reject
                    </button>

                    </div>

                    `;

                }
            );

        }
    );

}



function validateStop(stop_id, status) {

    fetch(
        "/validation/update",
        {
            method:"POST",

            headers:{
                "Content-Type":"application/json"
            },

            body:JSON.stringify(
                {
                    stop_id:stop_id,
                    status:status,
                    validator:"dashboard"
                }
            )
        }
    )

    .then(
        () => loadValidationQueue()
    );

}



loadValidationQueue();


"""

if "loadValidationQueue" not in text:

    text = text.replace(
        marker,
        insert + marker,
        1
    )

    p.write_text(text)

    print("Added validation queue JS")

else:
    print("Validation queue JS already exists")
