from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


replacements = {

'${props.location}':
'${props.location.replace("+", " at ")}',

'Score: ${props.score}<br>':
'Improvement priority score: ${props.score || "Not available"}<br>',

'Impact: ${props.impact}<br><br>':
'${props.impact ? "Community impact: " + props.impact + "<br>" : ""}<br>',

'<b>Projects</b><br>':
'<b>Current improvement projects</b><br>',

'No active projects<br>':
'No active improvement projects<br>',

'Adopt this stop':
'Become a community steward',

'<b>OSM Evidence</b><br>':
'<b>Existing stop information</b><br>',

'Bus stop mapped:':
'Transit stop confirmed:',

'Shelter:':
'Shelter appears to exist:',

'Bench:':
'Bench appears to exist:',

}

for old,new in replacements.items():

    text = text.replace(
        old,
        new
    )


p.write_text(text)

print(
    "Improved popup language"
)
