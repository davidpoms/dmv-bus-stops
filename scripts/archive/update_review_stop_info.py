from pathlib import Path

p = Path("src/dashboard/templates/review.html")

text = p.read_text()

old = '''<div id="stopInfo">
Loading stop information...
</div>'''

new = '''<div id="stopInfo">
<strong>Stop ID:</strong> {{ stop[0] }}<br>
<strong>Name:</strong> {{ stop[1] or "Unnamed stop" }}<br>
<strong>Jurisdiction:</strong> {{ stop[4] or "Unknown" }}<br>
<strong>Coordinates:</strong> {{ stop[2] }}, {{ stop[3] }}
</div>'''

if old not in text:
    raise Exception("stopInfo placeholder not found")

text = text.replace(old, new)

p.write_text(text)

print("Updated stop information display")
