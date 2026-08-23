from pathlib import Path

path = Path("src/dashboard/templates/review.html")

text = path.read_text(encoding="utf-8")

needle = """
console.log(result);

if(!response.ok){
"""

replacement = """
console.log(result);

if(result.message === "Review already submitted"){

    document.body.innerHTML = `

    <div class="completion-card">

    <h1>
    Review already submitted
    </h1>

    <p>
    This stop already has a completed community review.
    Thank you for helping improve bus stop information.
    </p>

    <button onclick="window.location.href='/dashboard'">
    Return to dashboard
    </button>

    </div>

    `;

    return;

}


if(!response.ok){
"""

if needle not in text:
    raise SystemExit(
        "Could not find insertion point"
    )

text = text.replace(
    needle,
    replacement,
    1
)

path.write_text(
    text,
    encoding="utf-8"
)

print("Added duplicate review message")