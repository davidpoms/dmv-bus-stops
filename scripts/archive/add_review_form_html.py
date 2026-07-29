from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

marker = '<div id="surveyContent"></div>'

insert = r'''

<div id="reviewForm" style="display:none;">

<h3>Community Stop Review</h3>

<label>Email (optional)</label>
<input id="reviewEmail" type="email">


<label>Waiting area type</label>
<select id="waitingArea">
<option value="sidewalk">Sidewalk</option>
<option value="platform">Platform</option>
<option value="grass">Grass</option>
<option value="other">Other</option>
</select>


<label>Concrete pad present?</label>
<select id="padPresent">
<option value="true">Yes</option>
<option value="false">No</option>
</select>


<label>Bench location feasible?</label>
<select id="benchFeasible">
<option value="true">Yes</option>
<option value="false">No</option>
</select>


<label>Sun exposure</label>
<select id="sunExposure">
<option value="shade">Shade</option>
<option value="partial">Partial</option>
<option value="full_sun">Full sun</option>
</select>


<label>Confidence</label>
<select id="confidence">
<option value="0.5">Medium</option>
<option value="0.8">High</option>
<option value="1.0">Certain</option>
</select>


<label>Notes</label>

<textarea id="reviewNotes"></textarea>


<button onclick="submitCurrentReview()">
Submit Review
</button>


</div>

'''

if "id=\"reviewForm\"" not in text:
    text = text.replace(marker, marker + insert)
    p.write_text(text)
    print("Added review form")
else:
    print("Review form already exists")
