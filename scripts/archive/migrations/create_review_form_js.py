from pathlib import Path

p = Path("src/dashboard/static/review.js")

p.write_text(r'''
function submitStopReview(stopId) {

    const payload = {

        stop_id: stopId,

        anonymous_email:
            document.getElementById("reviewEmail").value,

        concrete_pad_present:
            document.getElementById("padPresent").value,

        bench_location_feasible:
            document.getElementById("benchFeasible").value,

        waiting_area_type:
            document.getElementById("waitingArea").value,

        sun_exposure:
            document.getElementById("sunExposure").value,

        reviewer_confidence:
            document.getElementById("confidence").value,

        notes:
            document.getElementById("reviewNotes").value
    };


    fetch("/review/submit", {

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify(payload)

    })

    .then(r => r.json())

    .then(data => {

        alert(
            "Review saved!"
        );

        console.log(data);

    });

}
''')

print("Created review.js")
