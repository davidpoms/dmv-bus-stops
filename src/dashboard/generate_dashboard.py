"""
Generate live HTML implementation dashboard.
"""

import json
from pathlib import Path
from string import Template

from src.dashboard.data import (
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
        for x in top_counties(10)
    )


    municipality_list = "\n".join(
        f"""
        <tr>
            <td>{x['state']}</td>
            <td>{x['municipality']}</td>
            <td>{x['stop_count']}</td>
        </tr>
        """
        for x in top_municipalities(10)
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


    template = Template(
        TEMPLATE_FILE.read_text()
    )


    html = template.substitute(
        total_projects=data["total_projects"],
        status_list=status_list,
        geography_totals=geography_totals,
        county_list=county_list,
        municipality_list=municipality_list,
        ward_list=ward_list,

    )


    OUTPUT_FILE.write_text(html)


if __name__ == "__main__":
    generate_dashboard()
