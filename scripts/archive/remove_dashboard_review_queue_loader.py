from pathlib import Path

path = Path("src/dashboard/static/dashboard.js")

text = path.read_text()

start = text.find(
"""
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
"""
)

if start == -1:
    raise SystemExit("Queue loader block not found")


end = start + len(
"""
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
"""
)


text = text[:start] + text[end:]

path.write_text(text)

print("Removed dashboard review queue loader")
