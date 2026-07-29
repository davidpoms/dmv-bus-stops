from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

insert = """

document.addEventListener(
    "click",
    function(event) {

        if (
            event.target.classList.contains(
                "adoptStopButton"
            )
        ) {

            const stopId =
                event.target.dataset.stop;


            fetch(
                `/stops/${stopId}/community-action`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                        "application/json"
                    },

                    body: JSON.stringify(
                        {
                            status: "planned",
                            project_type:
                                "community_review",
                            steward:
                                "Dashboard Volunteer",
                            notes:
                                "Adopted through dashboard"
                        }
                    )
                }
            )
            .then(
                response => response.json()
            )
            .then(
                data => {

                    alert(
                        "Stop adopted!"
                    );

                    location.reload();

                }
            );

        }

    }
);

"""

text += insert

p.write_text(text)

print("adopt button handler added")
