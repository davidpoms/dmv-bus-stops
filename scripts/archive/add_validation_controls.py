from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
            Status:
            ${stop.status}

            </div>
"""

new = """
            Status:
            ${stop.status}

            <br><br>

            <button onclick="submitValidation(${stop.stop_id}, 'validated')">
            Confirm
            </button>

            <button onclick="submitValidation(${stop.stop_id}, 'rejected')">
            Reject
            </button>

            </div>
"""

if old in text:
    text = text.replace(old,new,1)

    insert = """

function submitValidation(stop_id, status){

    fetch("/validation/update", {

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body: JSON.stringify({

            stop_id: stop_id,

            status: status,

            validator:"dashboard_user",

            notes:"Updated from validation queue"

        })

    })

    .then(response => response.json())

    .then(data => {

        console.log(data);

        loadValidationQueue();

    });

}

"""

    text += insert

    p.write_text(text)

    print("Added validation controls")

else:
    print("Queue block not found")
