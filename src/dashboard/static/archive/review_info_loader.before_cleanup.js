document.addEventListener(
    "DOMContentLoaded",
    async () => {

        const stopId =
            window.location.pathname.split("/").pop();


        const container =
            document.getElementById("stopInfo");


        if (!container) {
            return;
        }


        try {

            const response =
                await fetch(
                    `/review/${stopId}/info`
                );


            const info =
                await response.json();

            console.log(
                "Loaded review info:",
                info
            );


            container.innerHTML = `
                <div class="panel">

                    <strong>
                    ${info.name || "Bus Stop"}
                    </strong>

                    <br>

                    Stop ID:
                    ${info.stop_id}

                    <br><br>

                    Coordinates:
                    ${info.lat.toFixed(5)},
                    ${info.lon.toFixed(5)}

                    <br><br>

                    Jurisdiction:
                    ${info.state || ""}
                    ${info.county ? " | " + info.county : ""}
                    ${info.municipality ? " | " + info.municipality : ""}

                    <br><br>

                    ${
                        info.wmata
                        ?
                        `
                        <div class="evidence-card">

                            <strong>
                            WMATA Transit Information
                            </strong>

                            <br><br>

                            WMATA Data Availability:
                            <span class="${
                                info.wmata.availability === "confirmed"
                                ? "wmata-confirmed"
                                : "wmata-unavailable"
                            }">
                            ${
                                info.wmata.availability === "confirmed"
                                ? "Confirmed WMATA match"
                                : "No WMATA match available"
                            }
                            </span>

                            <br><br>

                            WMATA Stop ID:
                            ${info.wmata.stop_id || "Unknown"}

                            <br>

                            Status:
                            ${
                                info.wmata.status === "PRS"
                                ? "Published stop"
                                : (info.wmata.status || "Unknown")
                            }

                            <br>

                            Shelter:
                            ${
                                info.wmata.shelter === "1"
                                ? "Yes"
                                : info.wmata.shelter === "0"
                                ? "No"
                                : "Unknown"
                            }

                            <br>

                            Bench:
                            ${
                                info.wmata.bench === "1"
                                ? "Yes"
                                : info.wmata.bench === "0"
                                ? "No"
                                : "Unknown"
                            }

                            <br>

                            Accessible:
                            ${
                                info.wmata.accessible === "Y"
                                ? "Yes"
                                : "No"
                            }

                            <br>

                            Match quality:
                            ${
                                info.wmata.match_confidence === "high"
                                ? "High confidence match (within ~10 meters)"
                                : info.wmata.match_confidence === "medium"
                                ? "Medium confidence match (within ~50 meters)"
                                : info.wmata.match_confidence === "low"
                                ? "Low confidence match (verify location)"
                                : "Unknown"
                            }

                            <br>

                            Match distance:
                            ${
                                info.wmata.match_distance_m !== null
                                ? (
                                    info.wmata.match_distance_m < 10
                                    ? info.wmata.match_distance_m.toFixed(1)
                                    : Math.round(info.wmata.match_distance_m)
                                ) + " meters"
                                : "Unknown"
                            }

                        </div>

                        <br>
                        `
                        :
                        ""
                    }

                    ${
                        info.wmata
                        ?
                        `
                        <br><br>

                        <div class="evidence-card">

                            <strong>
                            WMATA Stop Inventory
                            </strong>

                            <br><br>

                            Shelter:
                            ${
                                info.wmata.shelter === "1"
                                ? "Yes"
                                : "No"
                            }

                            <br>

                            Bench:
                            ${
                                info.wmata.bench === "1"
                                ? "Yes"
                                : "No"
                            }

                            <br>

                            Accessible boarding:
                            ${
                                info.wmata.accessible === "Y"
                                ? "Yes"
                                : "No"
                            }

                            <br>

                            Match confidence:
                            ${
                                info.wmata.match_confidence || "Unknown"
                            }

                        </div>
                        `
                        :
                        ""
                    }


                    ${
                        info.streetview_url
                        ?
                        `
                        <br><br>

                        <a
                            href="${info.streetview_url}"
                            target="_blank"
                            class="stop-review-button">

                            Open Google Street View

                        </a>
                        `
                        :
                        ""
                    }

                </div>
            `;


        } catch(error){

            console.error(
                "Failed loading stop info",
                error
            );

            container.innerHTML =
                "Unable to load stop information.";

        }

    }
);
