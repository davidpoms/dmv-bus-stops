from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
            <button onclick="event.stopPropagation(); submitValidation(${stop.stop_id}, 'validated')">
            Verified
            </button>

            <button onclick="event.stopPropagation(); submitValidation(${stop.stop_id}, 'rejected')">
            Incorrect
            </button>

            <button onclick="event.stopPropagation(); submitValidation(${stop.stop_id}, 'uncertain')">
            Unable to determine
            </button>
"""

new = """
            <label>
            Shelter:
            <select id="shelter_${stop.stop_id}"
            onclick="event.stopPropagation();">
                <option value="yes">Yes</option>
                <option value="no">No</option>
                <option value="unknown">Unknown</option>
            </select>
            </label>

            <br>

            <label>
            Bench:
            <select id="bench_${stop.stop_id}"
            onclick="event.stopPropagation();">
                <option value="yes">Yes</option>
                <option value="no">No</option>
                <option value="unknown">Unknown</option>
            </select>
            </label>

            <br>

            <label>
            Trash:
            <select id="trash_${stop.stop_id}"
            onclick="event.stopPropagation();">
                <option value="yes">Yes</option>
                <option value="no">No</option>
                <option value="unknown">Unknown</option>
            </select>
            </label>

            <br>

            <label>
            Space for bench:
            <select id="bench_feasible_${stop.stop_id}"
            onclick="event.stopPropagation();">
                <option value="yes">Yes</option>
                <option value="no">No</option>
                <option value="unknown">Unknown</option>
            </select>
            </label>

            <br>

            <label>
            ADA clearance:
            <select id="ada_${stop.stop_id}"
            onclick="event.stopPropagation();">
                <option value="yes">Yes</option>
                <option value="no">No</option>
                <option value="unknown">Unknown</option>
            </select>
            </label>

            <br><br>

            <textarea
            id="notes_${stop.stop_id}"
            placeholder="Notes"
            onclick="event.stopPropagation();"></textarea>

            <br>

            <button
            onclick="event.stopPropagation(); submitObservation(${stop.stop_id})">
            Submit Survey
            </button>
"""

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text)
    print("Replaced validation buttons with survey form")
else:
    print("Old validation buttons not found")
