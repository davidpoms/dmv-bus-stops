from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

start = text.find("""
<h2>
Geography Overview
</h2>
""")

end = text.find("""
<h2>
Review Pipeline Coverage
</h2>
""")

if start == -1:
    raise SystemExit("Geography start missing")

if end == -1:
    # current template may still say Pipeline Coverage
    end = text.find("""
<h2>
Pipeline Coverage
</h2>
""")

if end == -1:
    raise SystemExit("Pipeline section missing")


replacement = """
<h2>
Geography Overview
</h2>


<h3>
Stops by State
</h3>

<div class="geo-grid">
$geography_totals
</div>


<h3>
Top Counties
</h3>

<table class="geo-table">
<tr>
<th>State</th>
<th>County</th>
<th>Stops</th>
</tr>

$county_list

</table>


<h3>
Top Municipalities
</h3>

<table class="geo-table">
<tr>
<th>State</th>
<th>Municipality</th>
<th>Stops</th>
</tr>

$municipality_list

</table>


<h3>
DC Wards
</h3>

<table class="geo-table">
<tr>
<th>Ward</th>
<th>Stops</th>
</tr>

$ward_list

</table>


<h3>
DC Advisory Neighborhood Commissions
</h3>

<table class="geo-table">
<tr>
<th>ANC</th>
<th>Stops</th>
</tr>

$anc_list

</table>

"""

text = text[:start] + replacement + text[end:]

p.write_text(text)

print("Restored geography section")
