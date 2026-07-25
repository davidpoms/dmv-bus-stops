from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

if "Community Verification Progress" in text:
    print("Metric cards already present")
    raise SystemExit

insert_before = """
</body>
"""

cards = """
<div class="card">
<h2>Community Verification Progress</h2>

<p>
Stops reviewed:
${REVIEWED_STOPS}
</p>

<p>
Consensus verified:
${CONSENSUS_STOPS}
</p>

<p>
Verification coverage:
${VERIFICATION_COVERAGE}
</p>

</div>


<div class="card">
<h2>Bench Verification</h2>

<p>
OSM bench records:
${OSM_BENCHES}
</p>

<p>
Community confirmed benches:
${COMMUNITY_BENCHES}
</p>

<p>
Bench opportunities:
${BENCH_OPPORTUNITIES}
</p>

</div>


<div class="card">
<h2>Route Validation</h2>

<p>
Total routes:
${TOTAL_ROUTES}
</p>

<p>
Fully validated routes:
${FULLY_VERIFIED_ROUTES}
</p>

<p>
Partially validated routes:
${PARTIAL_ROUTES}
</p>

</div>


</body>
"""

if insert_before not in text:
    raise SystemExit("Could not find body close")

text = text.replace(insert_before, cards)

p.write_text(text)

print("Added dashboard metric cards")
