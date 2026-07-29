from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

insert = """

document.addEventListener(
    "click",
    function(event) {

        if (
            event.target.classList.contains(
                "installStopButton"
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
                            status: "installed",
                            project_type:
                                "community_improvement",
                            steward:
                                "Dashboard Volunteer",
                            notes:
                                "Marked installed through dashboard"
                        }
                    )
                }
            )
            .then(
                response => response.json()
            )
            .then(
                data => {

                    if (
                        data.status === "already_exists"
                    ) {
                        alert(
                            "This stop already has an active action."
                        );
                    }
                    else {
                        alert(
                            "Installation recorded!"
                        );
                    }

                    location.reload();

                }
            );

        }

    }
);

"""

text += insert

p.write_text(text)

print("install handler added")
