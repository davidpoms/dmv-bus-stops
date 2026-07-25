from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

text = text.replace(
"""
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
""",
"""
<p>
Community confirmed benches:
${COMMUNITY_BENCHES}
</p>

<p>
Bench opportunities:
${BENCH_OPPORTUNITIES}
</p>

<p>
Stops needing bench review:
${STOPS_NEEDING_REVIEW}
</p>
"""
)

p.write_text(text)

print("Updated bench dashboard card")
