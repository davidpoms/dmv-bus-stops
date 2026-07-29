from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

js = ROOT / "src/dashboard/static/dashboard.js"
html = ROOT / "src/dashboard/templates/dashboard.html"

# ---- JS patch ----

text = js.read_text()

if "loadReviewQueue" not in text:

    text += r'''

// -------------------------------
// Review queue loader
// -------------------------------

function loadReviewQueue(){

    fetch("/api/review-queue")
    .then(r => r.json())
    .then(data => {

        const container =
            document.getElementById("reviewQueue");

        if (!container){
            console.log(
                "reviewQueue container missing"
            );
            return;
        }


        container.innerHTML = "";


        data.queue.forEach(stop => {

            container.innerHTML += `

            <div class="review-card">

                <h4>
                ${stop.location_name || "Bus Stop"}
                </h4>

                <p>
                Priority:
                ${stop.priority}
                </p>

                <p>
                Opportunity:
                ${stop.evidence.opportunity_score}
                </p>

                <button
                onclick="window.location='/survey-page/${stop.stop_id}'">
                Review Stop
                </button>

            </div>

            `;

        });

    });

}


document.addEventListener(
"DOMContentLoaded",
function(){

    if(
        document.getElementById(
            "reviewQueue"
        )
    ){
        loadReviewQueue();
    }

});

'''

    js.write_text(text)


# ---- HTML patch ----

html_text = html.read_text()

if 'id="reviewQueue"' not in html_text:

    html_text = html_text.replace(
        "<h3>Community Stop Review</h3>",
        """
<h3>Community Stop Review</h3>

<div id="reviewQueue">
Loading review queue...
</div>
"""
    )

html.write_text(html_text)


print("Dashboard review flow patched")
