from pathlib import Path

p = Path("src/dashboard/generate_dashboard.py")

text = p.read_text()

# add import
text = text.replace(
    "from src.dashboard.data import (\n",
    "from src.dashboard.data import (\n    dashboard_metrics,\n"
)

# add metric variables before template substitution
marker = """
    html = template.substitute(
"""

replacement = """
    metrics = dashboard_metrics()

    html = template.substitute(
        STOP_COUNT=f"{metrics['verification']['total_stops']:,}",
        REVIEWED_STOPS=f"{metrics['verification']['reviewed_stops']:,}",
        CONSENSUS_STOPS=f"{metrics['verification']['consensus_stops']:,}",
        VERIFICATION_COVERAGE=f"{metrics['coverage']['coverage_percent']}%",
        OSM_BENCHES=f"{metrics['benches']['osm_bench_features']:,}",
        COMMUNITY_BENCHES=f"{metrics['benches']['community_benches']:,}",
        BENCH_OPPORTUNITIES=f"{metrics['benches']['community_bench_opportunities']:,}",
        TOTAL_ROUTES=f"{metrics['routes']['total_routes']:,}",
        FULLY_VERIFIED_ROUTES=f"{metrics['routes']['fully_verified_routes']:,}",
        PARTIAL_ROUTES=f"{metrics['routes']['partially_verified_routes']:,}",
"""

if marker not in text:
    raise SystemExit("Could not find template substitution block")

text = text.replace(marker, replacement)

p.write_text(text)

print("Added dashboard metric injection")
