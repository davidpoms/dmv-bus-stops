
const stop_id =
window.location.pathname.split("/").pop();


fetch("/survey/" + stop_id)

.then(response => response.json())

.then(stop => {


document.getElementById("review").innerHTML = `


<div class="container">


<div class="panel">

<h2>
${stop.location}
</h2>


<p>
Stop ID: ${stop.stop_id}
</p>


<p>
Latitude:
${stop.lat}
<br>
Longitude:
${stop.lon}
</p>


<br>


<a href="${stop.streetview_url}" target="_blank">

<button>
Open Google Street View
</button>

</a>


</div>




<div class="panel">


<h2>
Observation
</h2>


<div class="question">
Shelter present:

<br>

<select id="shelter">
<option value="yes">Yes</option>
<option value="no">No</option>
<option value="unknown">Unknown</option>
</select>

</div>



<div class="question">
Bench present:

<br>

<select id="bench">
<option value="yes">Yes</option>
<option value="no">No</option>
<option value="unknown">Unknown</option>
</select>

</div>




<div class="question">
</div>




<div class="question">

Space for bench without blocking ADA?

<br>

<select id="bench_feasible">
<option value="yes">Yes</option>
<option value="no">No</option>
<option value="unknown">Unknown</option>
</select>

</div>




<div class="question">

ADA clearance possible?

<br>

<select id="ada">
<option value="yes">Yes</option>
<option value="no">No</option>
<option value="unknown">Unknown</option>
</select>

</div>




<div class="question">

Notes:

<textarea id="notes"></textarea>

</div>



<button onclick="submitSurvey()">
Submit Review
</button>


</div>


</div>


`;



});




function submitSurvey(){


fetch("/observations/create",
{

method:"POST",

headers:{
"Content-Type":"application/json"
},


body:JSON.stringify({

stop_id: stop_id,

observer:"dashboard_user",

shelter_present:
document.getElementById("shelter").value,

bench_present:
document.getElementById("bench").value,

trash_present:
document.getElementById("trash").value,

bench_feasible:
document.getElementById("bench_feasible").value,

ada_clearance_possible:
document.getElementById("ada").value,

notes:
document.getElementById("notes").value

})

})


.then(r=>r.json())

.then(data=>{

alert("Review saved");

window.location="/dashboard";

});


}

