from pathlib import Path

p = Path("src/dashboard/generate_dashboard.py")

text = p.read_text()

text = text.replace(
"""
        OSM_BENCHES=f"{metrics['benches']['osm_bench_features']:,}",
        COMMUNITY_BENCHES=f"{metrics['benches']['community_benches']:,}",
        BENCH_OPPORTUNITIES=f"{metrics['benches']['community_bench_opportunities']:,}",
""",
"""
        COMMUNITY_BENCHES=f"{metrics['benches']['community_confirmed_benches']:,}",
        BENCH_OPPORTUNITIES=f"{metrics['benches']['community_bench_opportunities']:,}",
        STOPS_NEEDING_REVIEW=f"{metrics['benches']['stops_needing_review']:,}",
"""
)

p.write_text(text)

print("Fixed bench substitutions")
