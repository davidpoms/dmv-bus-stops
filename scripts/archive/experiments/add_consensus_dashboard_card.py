from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

marker = """
<div class="card">
<h2>Community Verification Progress</h2>
"""

card = """
<div class="card">
<h2>Consensus Verification Pipeline</h2>

<p>
Completed reviews:
${COMPLETED_REVIEWS}
</p>

<p>
Pending assignments:
${PENDING_REVIEWS}
</p>

<p>
Stops reaching consensus:
${VERIFIED_STOPS}
</p>

</div>


"""

if "Consensus Verification Pipeline" not in text:
    text=text.replace(marker, card+marker, 1)

p.write_text(text)

print("Added consensus dashboard card")
