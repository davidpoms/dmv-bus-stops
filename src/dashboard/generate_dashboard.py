"""
Generate static HTML implementation dashboard.
"""

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE_DIR /
    "implementation_summary.json"
)

OUTPUT_FILE = (
    BASE_DIR /
    "dmv_bus_stops_dashboard.html"
)


def generate_dashboard():

    with open(INPUT_FILE) as f:
        data = json.load(f)


    html = f"""
<!DOCTYPE html>
<html>

<head>

<title>
DMV Bus Stop Improvement Dashboard
</title>

<style>

body {{
    font-family: Arial, sans-serif;
    margin: 40px;
}}

.card {{
    display:inline-block;
    padding:20px;
    margin:10px;
    border:1px solid #ccc;
}}

table {{
    border-collapse:collapse;
    width:100%;
}}

td, th {{
    border:1px solid #ddd;
    padding:8px;
}}

</style>

</head>


<body>

<h1>
DMV Bus Stop Improvement Dashboard
</h1>


<div class="card">
<h2>{data["total_projects"]}</h2>
<p>Active Projects</p>
</div>


<h2>
Project Status
</h2>

<ul>
"""

    for status, count in data["project_status"].items():

        html += f"""
<li>{status}: {count}</li>
"""


    html += """
</ul>

<h2>
Impact Levels
</h2>

<ul>
"""


    for impact, count in data["impact_levels"].items():

        html += f"""
<li>{impact}: {count}</li>
"""


    html += """
</ul>


<h2>
Top Priority Stops
</h2>

<table>

<tr>
<th>Rank</th>
<th>Stop</th>
<th>Location</th>
<th>Score</th>
<th>Impact</th>
</tr>
"""


    for i, stop in enumerate(
        data["top_priority_stops"],
        start=1
    ):

        html += f"""
<tr>
<td>{i}</td>
<td>{stop["stop_id"]}</td>
<td>{stop["location"]}</td>
<td>{stop["score"]}</td>
<td>{stop["impact"]}</td>
</tr>
"""


    html += """

</table>

</body>

</html>
"""


    OUTPUT_FILE.write_text(
        html
    )


    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":

    generate_dashboard()
