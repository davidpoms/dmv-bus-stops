from pathlib import Path

template = Path("src/dashboard/templates/stop_detail.html")
js = Path("src/dashboard/static/stop_detail.js")


template.write_text(
"""<!DOCTYPE html>
<html>

<head>

<title>Bus Stop Profile</title>

<link rel="stylesheet" href="/static/dashboard.css">

<script>
const stopId = {{ stop_id }};
</script>

</head>


<body>


<div class="panel">

<h1 id="name">
Loading stop...
</h1>


<div id="details">
Loading information...
</div>


</div>


<script src="/static/stop_detail.js"></script>


</body>

</html>
""",
encoding="utf-8"
)


js.write_text(
r"""
async function loadStopProfile(){

    const details =
        document.getElementById("details");


    try {

        const stopResponse =
            await fetch(`/stops/${stopId}`);

        const stop =
            await stopResponse.json();


        const reviewResponse =
            await fetch(`/review/${stopId}/info`);

        const review =
            await reviewResponse.json();



        document.getElementById("name").innerHTML =
            stop.location || review.name || "Bus Stop";



        details.innerHTML = `

        <div class="card">

        <strong>Location</strong><br>

        ${stop.location || review.name}

        <br><br>

        Stop ID:
        ${stop.stop_id}

        <br><br>

        Routes:
        ${(stop.routes || []).join(", ")}

        </div>



        <div class="card">

        <strong>Rider exposure</strong>

        <br><br>

        Estimated weekday boardings:

        <strong>
        ${
            review.impact_summary
            ?.estimated_weekday_boardings
            ?.toLocaleString()
            || "Unknown"
        }
        </strong>


        <br><br>

        Opportunity score:

        <strong>
        ${stop.score || "Unknown"}
        </strong>


        </div>



        <div class="card">

        <strong>
        Current stop information
        </strong>

        <br><br>

        WMATA status:

        ${
            review.wmata?.status || "Unknown"
        }

        <br>

        Shelter:

        ${
            review.wmata?.shelter == 1
            ? "Yes"
            : "No"
        }

        <br>

        Bench:

        ${
            review.wmata?.bench == 1
            ? "Yes"
            : "No"
        }


        </div>



        <div class="card">

        <strong>
        Community verification
        </strong>

        <br><br>

        Reviews completed:

        ${
            review.community_reviews?.review_count || 0
        }


        <br><br>

        <a
        class="stop-review-button"
        href="/review/${stopId}?mode=direct">

        Review this stop

        </a>


        <br><br>


        <a
        class="stop-review-button"
        href="${stop.streetview_url}"
        target="_blank">

        Open Street View

        </a>


        </div>

        `;



    }
    catch(error){

        console.error(
            "Failed loading stop profile",
            error
        );

        details.innerHTML =
            "Unable to load stop information.";

    }

}


loadStopProfile();

""",
encoding="utf-8"
)


print("Built stop profile page")
