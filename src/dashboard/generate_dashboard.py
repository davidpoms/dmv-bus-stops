"""
Generate live HTML implementation dashboard.
"""

import json
from pathlib import Path
from string import Template

from src.dashboard.data import (
    counties,
    municipalities,
    dc_ancs,
    dashboard_metrics,
    jurisdiction_totals,
    top_counties,
    top_municipalities,
    dc_wards,
)


BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "implementation_summary.json"

TEMPLATE_FILE = (
    BASE_DIR /
    "src/dashboard/templates/dashboard.html"
)

OUTPUT_FILE = (
    BASE_DIR /
    "dmv_bus_stops_dashboard.html"
)



def query_count(sql):
    import sqlite3

    db = BASE_DIR / "src/database/dmv_bus_stops.db"

    conn = sqlite3.connect(db)
    count = conn.execute(sql).fetchone()[0]
    conn.close()

    return count

def generate_dashboard():

    with open(INPUT_FILE) as f:
        data = json.load(f)


    status_list = "\n".join(
        f"<li>{status}: {count}</li>"
        for status, count in data["project_status"].items()
    )


    geography_totals = "\n".join(
        f"""
        <div class="geo-card">
            <div class="geo-number">{x['stop_count']}</div>
            <div class="geo-label">{x['state']} stops</div>
        </div>
        """
        for x in jurisdiction_totals()
    )




    county_list = "\n".join(
        f"""
        <tr>
            <td>{x['state']}</td>
            <td>{x['county']}</td>
            <td>{x['stop_count']}</td>
        </tr>
        """
        for x in counties()
    )


    municipality_list = "\n".join(
        f"""
        <tr>
            <td>{x['state']}</td>
            <td>{x['county']}</td>
            <td>{x['municipality']}</td>
            <td>{x['stop_count']}</td>
        </tr>
        """
        for x in municipalities()
    )


    ward_list = "\n".join(
        f"""
        <tr>
            <td>Ward {x['dc_ward']}</td>
            <td>{x['stop_count']}</td>
        </tr>
        """
        for x in dc_wards()
    )


    anc_list = "\n".join(
        f"""
        <tr>
            <td>{x['dc_anc']}</td>
            <td>{x['stop_count']}</td>
        </tr>
        """
        for x in dc_ancs()
    )


    template = Template(
        TEMPLATE_FILE.read_text()
    )


    metrics = dashboard_metrics()

    geography = {
        "counties": counties(),
        "municipalities": municipalities(),
        "dc_ancs": dc_ancs(),
    }

    html = template.substitute(
        STOP_COUNT=f"{metrics['verification']['total_stops']:,}",
        REVIEWED_STOPS=f"{metrics['verification']['reviewed_stops']:,}",
        CONSENSUS_STOPS=f"{metrics['verification']['consensus_stops'] or 0:,}",
        VERIFICATION_COVERAGE=f"{metrics['coverage']['coverage_percent']}%",
        COMMUNITY_BENCHES=f"{metrics['benches']['community_confirmed_benches']:,}",
        BENCH_OPPORTUNITIES=f"{metrics['benches']['community_bench_opportunities']:,}",
        STOPS_NEEDING_REVIEW=f"{metrics['benches']['stops_needing_review']:,}",
        TOTAL_ROUTES=f"{metrics['routes']['total_routes']:,}",
        FULLY_VERIFIED_ROUTES=f"{metrics['routes']['fully_verified_routes']:,}",
        PARTIAL_ROUTES=f"{metrics['routes']['partially_verified_routes']:,}",        total_projects=data["total_projects"],
        status_list=status_list,
        geography_totals=geography_totals,
        county_list=county_list,
        municipality_list=municipality_list,
        anc_list=anc_list,
        ward_list=ward_list,

    )


    OUTPUT_FILE.write_text(html)


if __name__ == "__main__":
    generate_dashboard()
