"""
Generate live HTML implementation dashboard.
"""

from pathlib import Path
from string import Template

from src.dashboard.render_docs import render_markdown_file

from src.dashboard.data import (
    counties,
    municipalities,
    dc_ancs,
    dashboard_metrics,
    jurisdiction_totals,
    dc_wards,
)


BASE_DIR = Path(__file__).resolve().parents[2]

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


    methodology_html = render_markdown_file(
        "DMV_Bus_Stop_Intelligence_Handbook.md"
    )

    volunteer_review_html = render_markdown_file(
        "Volunteer_Review_Handbook.md"
    )


    template = Template(
        TEMPLATE_FILE.read_text(encoding="utf-8")
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
        PARTIAL_ROUTES=f"{metrics['routes']['partially_verified_routes']:,}",

        COMPLETED_REVIEWS=f"{metrics['consensus']['completed_reviews']:,}",
        PENDING_REVIEWS=f"{metrics['consensus']['pending_reviews']:,}",
        VERIFIED_STOPS=f"{metrics['consensus']['verified_stops']:,}",
        geography_totals=geography_totals,
        county_list=county_list,
        municipality_list=municipality_list,
        anc_list=anc_list,
        ward_list=ward_list,

        METHODOLOGY_HTML=methodology_html,

        VOLUNTEER_REVIEW_HTML=volunteer_review_html,

    )


    OUTPUT_FILE.write_text(
    html,
    encoding="utf-8"
    )


if __name__ == "__main__":
    generate_dashboard()
