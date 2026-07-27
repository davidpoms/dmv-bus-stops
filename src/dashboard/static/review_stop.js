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


            info.innerHTML = `
                <strong>${data.location}</strong>
                <br>
                Stop ID: ${data.stop_id}
                <br>
                Coordinates:
                ${data.lat.toFixed(5)},
                ${data.lon.toFixed(5)}
                <br><br>
                <a href="${data.streetview_url}"
                   target="_blank">
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
