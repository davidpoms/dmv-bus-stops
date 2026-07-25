
let currentReviewStop = null;


function openReview(stopId){

    currentReviewStop = stopId;

    document.getElementById(
        "reviewForm"
    ).style.display = "block";

}


function submitCurrentReview(){

    const payload = {

        stop_id: currentReviewStop,

        anonymous_email:
            document.getElementById("reviewEmail").value,

        waiting_area_type:
            document.getElementById("waitingArea").value,

        concrete_pad_present:
            document.getElementById("padPresent").value,

        bench_location_feasible:
            document.getElementById("benchFeasible").value,

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

    .then(response => response.json())

    .then(data => {

        alert("Review saved");

        console.log(data);

    });

}
