from pathlib import Path

p = Path("src/dashboard/static/review_survey.js")

text = p.read_text()

addition = r'''

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

'''

if "loadReviewStopInfo" not in text:
    text += addition

p.write_text(text)

print("Added review stop info loader")
