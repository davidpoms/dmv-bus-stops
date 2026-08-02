document.addEventListener(
    "DOMContentLoaded",
    async () => {

        const stopId =
            window.location.pathname.split("/").pop();


        const info =
            document.getElementById("stopInfo");


        if(!info){
            return;
        }


        try {

            const response =
                await fetch(
                    `/survey/${stopId}`
                );


            if(!response.ok){
                throw new Error(
                    "Failed loading stop"
                );
            }


            const data =
                await response.json();

            console.log(
                "Survey data:",
                data
            );


            const streetview =
                `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${data.lat},${data.lon}`;


            info.innerHTML = `
                <strong>${data.location}</strong>
                <br><br>

                Stop ID: ${data.stop_id}

                <br><br>


                ${
                    data.ridership_exposure
                    ?
                    `
                    <strong>Transit demand</strong>
                    <br><br>

                    Routes serving this stop carry approximately

                    <strong>
                    ${data.ridership_exposure.average_weekday_boardings.toLocaleString()}
                    weekday boardings per day
                    </strong>

                    on average.

                    <br>

                    Routes:
                    ${data.ridership_exposure.routes.join(", ")}

                    <br><br>
                    `
                    :
                    ""
                }

                Existing stop information:
                <br>
                Coordinates:
                ${data.lat.toFixed(5)},
                ${data.lon.toFixed(5)}

                ${
                    data.wmata_evidence
                    ?
                    `
                    <br><br>

                    <strong>WMATA-reported stop amenities</strong>
                    <br><br>

                    Shelter:
                    ${
                        data.wmata_evidence.shelter === "1"
                        ? "Yes"
                        : "No"
                    }

                    <br>

                    Bench:
                    ${
                        data.wmata_evidence.bench === "1"
                        ? "Yes"
                        : "No"
                    }

                    <br>

                    Accessible:
                    ${
                        data.wmata_evidence.accessible === "Y"
                        ? "Yes"
                        : "No"
                    }

                    <br>

                    Data match confidence:
                    ${data.wmata_evidence.confidence}

                    `
                    :
                    ""
                }

                <br><br>

                <a
                href="${streetview}"
                target="_blank"
                class="stop-review-button">
                Open Street View
                </a>
            `;


        } catch(error){

            console.error(
                error
            );

            info.innerHTML =
                "Unable to load stop information.";

        }

    }
);
