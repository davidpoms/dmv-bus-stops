from pathlib import Path

path = Path(
    "src/dashboard/templates/review.html"
)

text = path.read_text()

start = text.index("<h3>Shelter</h3>")
end = text.index("<h3>Notes</h3>")


new_questions = r"""
<h3>Review mode</h3>

<label>
How are you reviewing this stop?
</label>

<select name="review_mode">

<option value="remote">
Remote (Street View / online)
</option>

<option value="in_person">
In person
</option>

</select>



<h3>Shelter</h3>

<label>
Is there a shelter at this stop?
</label>

<select name="shelter_present">

<option value="yes">Yes</option>
<option value="no">No</option>
<option value="unknown">Unsure</option>

</select>



<h3>Seating</h3>

<label>
Is there usable seating available for riders?
</label>

<select name="bench_present">

<option value="yes">Yes</option>
<option value="no">No seating</option>
<option value="unknown">Unsure</option>

</select>



<h3>Seating details</h3>

<label>
What type of seating is present?
</label>

<select name="bench_type">

<option value="">
Unknown
</option>

<option value="backed">
Bench with back
</option>

<option value="angled">
Angled/backless bench
</option>

<option value="individual">
Individual seats
</option>

<option value="other">
Other
</option>

</select>



<label>
Does the seating have a back?
</label>

<select name="bench_back">

<option value="yes">Yes</option>
<option value="no">No</option>
<option value="unknown">Unsure</option>

</select>



<label>
Are there hostile design features?
</label>

<select name="bench_hostile_features">

<option value="none">
None observed
</option>

<option value="separators">
Seat separators
</option>

<option value="other">
Other
</option>

<option value="unknown">
Unknown
</option>

</select>



<h3>Bench installation opportunity</h3>


<label>
If a bench were installed, could people still pass through safely?
</label>

<select name="bench_feasible">

<option value="yes">Yes</option>
<option value="no">No</option>
<option value="unknown">Unsure</option>

</select>



<label>
Would a concrete pad likely be necessary to install a bench without blocking accessibility?
</label>

<select name="concrete_pad_needed">

<option value="yes">Yes</option>
<option value="no">No</option>
<option value="unknown">Unsure</option>

</select>



<h3>Accessibility</h3>

<label>
Is the path to the stop accessible for riders using mobility devices?
</label>

<select name="accessibility_status">

<option value="good">
Clear
</option>

<option value="blocked">
Blocked
</option>

<option value="unknown">
Unsure
</option>

</select>



<h3>Rider comfort</h3>

<label>
How comfortable does this stop appear for waiting riders?
</label>

<select name="rider_comfort_category">

<option value="comfortable">
Comfortable
</option>

<option value="basic">
Basic
</option>

<option value="poor">
Poor
</option>

<option value="unknown">
Unsure
</option>

</select>



<h3>In-person observations</h3>

<label>
How busy does this stop appear?
</label>

<select name="rider_activity">

<option value="low">
Low activity
</option>

<option value="moderate">
Moderate activity
</option>

<option value="high">
High activity
</option>

<option value="very_high">
Very high activity
</option>

</select>



<label>
When does this stop appear busiest?
</label>

<textarea name="usage_times"></textarea>



<h3>Stop steward opportunity</h3>

<label>
Would you be willing to help contact nearby property owners about a possible bench installation?
</label>

<select name="property_owner_outreach">

<option value="yes">
Yes
</option>

<option value="maybe">
Maybe
</option>

<option value="no">
No
</option>

</select>



<label>
Email address (if willing to help)
</label>

<input
type="email"
name="steward_email"
>



"""

text = (
    text[:start]
    + new_questions
    + text[end:]
)

path.write_text(text)

print(
    "Updated community review questions."
)
