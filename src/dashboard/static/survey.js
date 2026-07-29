const stopId = window.location.pathname.split("/").pop();

fetch(`/survey/${stopId}`)
    .then(response => response.json())
    .then(data => {

        document.getElementById("review").innerHTML = `
            <div class="panel">

                <h2>${data.location}</h2>

                <p>
                    Coordinates:
                    ${data.lat},
                    ${data.lon}
                </p>

                <p>
                    Road heading:
                    ${data.heading ?? "unknown"}°
                </p>

                <a 
                  href="${data.streetview_url}"
                  target="_blank"
                >
                    Open Google Street View
                </a>

            </div>
        `;

    })
    .catch(error => {
        document.getElementById("review").innerHTML =
            "Failed loading stop data";
        console.error(error);
    });
