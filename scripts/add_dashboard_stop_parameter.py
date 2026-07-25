from pathlib import Path

files = list(Path("src").rglob("*.js"))

target = None

for f in files:
    text = f.read_text()
    if "submitCurrentReview" in text or "review" in f.name:
        target = f
        break

if not target:
    raise Exception("Could not find dashboard JS")

text = target.read_text()

addition = r'''

// Open a stop automatically when linked from reviewer queue

function loadStopFromURL() {

    const params = new URLSearchParams(
        window.location.search
    );

    const stop = params.get("stop");

    if (!stop) {
        return;
    }


    if (typeof selectStop === "function") {
        selectStop(Number(stop));
        return;
    }


    if (typeof loadStop === "function") {
        loadStop(Number(stop));
        return;
    }


    console.log(
        "Stop requested:",
        stop
    );
}


document.addEventListener(
    "DOMContentLoaded",
    loadStopFromURL
);

'''

if "loadStopFromURL" not in text:
    text += addition

target.write_text(text)

print("Updated dashboard stop URL handling:", target)
