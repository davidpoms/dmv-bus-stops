from pathlib import Path

p = Path("src/dashboard/templates/review.html")
text = p.read_text()

old = """await fetch(
"/review/submit",
{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:
JSON.stringify(payload)
}
);


alert(
"Review submitted. Thank you!"
);
"""

new = """const response =
await fetch(
"/review/submit",
{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:
JSON.stringify(payload)
}
);

const result =
await response.json();

console.log(result);

if(!response.ok){

    alert(
        JSON.stringify(result)
    );

    return;

}

alert(
"Review submitted. Thank you!"
);
"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text)
    print("Added review error reporting.")
else:
    print("Could not find submit block.")
