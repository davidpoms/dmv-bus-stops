from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

old = """
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
"""

new = """
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

if old not in text:
    print("Existing DC ward block not found; searching fallback")

    marker = "$ward_list"

    if marker in text and "$anc_list" not in text:
        text = text.replace(
            marker,
            marker + """

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
"""
        )
        print("Added ANC table after ward table")
    else:
        print("No changes made")
else:
    text = text.replace(old, new)
    print("Replaced DC ward section with ward + ANC sections")

p.write_text(text)
