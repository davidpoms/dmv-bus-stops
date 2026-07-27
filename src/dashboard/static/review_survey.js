document.addEventListener(
    "DOMContentLoaded",
    () => {


        function getReviewMode(){

            const radio =
                document.querySelector(
                    'input[name="review_mode"]:checked'
                );

            if(radio){
                return radio.value;
            }


            const select =
                document.querySelector(
                    'select[name="review_mode"]'
                );

            if(select){
                return select.value;
            }


            return "remote";
        }



        function updateSections(){

            const mode = getReviewMode();


            document
            .querySelectorAll(
                ".survey-section"
            )
            .forEach(section => {

                const sectionMode =
                    section.dataset.reviewMode;


                if(sectionMode === "remote"){

                    // Remote questions are baseline.
                    // Always show them.
                    section.style.display =
                        "block";

                }


                else if(sectionMode === "in_person"){

                    // Extra observations only.
                    section.style.display =
                        mode === "in_person"
                        ? "block"
                        : "none";

                }


                else if(sectionMode === "steward"){

                    // Steward questions always available.
                    section.style.display =
                        "block";

                }

            });

        }



        document
        .querySelectorAll(
            'input[name="review_mode"], select[name="review_mode"]'
        )
        .forEach(control => {

            control.addEventListener(
                "change",
                updateSections
            );

        });


        updateSections();

    }
);


async function loadReviewStopInfo(){

    const parts =
        window.location.pathname.split("/");

    const stopId =
        parts[parts.length - 1];

    if(!stopId){
        return;
    }


    try {

        const response =
            await fetch(
                `/review/${stopId}/info`
            );


        const info =
            await response.json();


        const container =
            document.getElementById(
                "stopInfo"
            );


        if(!container){
            return;
        }


        let geography = "";


        if(info.state === "DC"){

            geography =
                `
                DC
                ${info.ward ? " | Ward " + info.ward : ""}
                ${info.anc ? " | ANC " + info.anc : ""}
                `;

        } else {

            geography =
                `
                ${info.state || ""}
                ${info.county ? " | " + info.county : ""}
                ${info.municipality ? " | " + info.municipality : ""}
                `;

        }


        container.innerHTML =
            `
            <strong>${info.name || "Bus Stop"}</strong>
            <br>
            Stop ID: ${info.stop_id}
            <br>
            Coordinates:
            ${info.lat.toFixed(5)},
            ${info.lon.toFixed(5)}
            <br>
            Jurisdiction:
            ${geography}
            `;


    } catch(err){

        console.error(
            "Could not load stop info",
            err
        );

    }

}


document.addEventListener(
    "DOMContentLoaded",
    loadReviewStopInfo
);

