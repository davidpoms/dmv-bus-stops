from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

marker = """
function loadValidationQueue(){
"""

insert = """
function focusValidationStop(stop_id) {

    fetch(`/stops/${stop_id}`)

    .then(
        response => response.json()
    )

    .then(
        stop => {

            map.setView(
                [
                    stop.latitude,
                    stop.longitude
                ],
                16
            );

        }
    );

}



"""

if "function focusValidationStop" not in text:
    text = text.replace(marker, insert + marker, 1)
    p.write_text(text)
    print("Added validation focus function")
else:
    print("Function already exists")
