from pathlib import Path

p = Path("src/dashboard/generate_dashboard.py")

text = p.read_text()

text = text.replace(
    "from src.dashboard.data import (",
    "from src.dashboard.data import (\n    counties,\n    municipalities,\n    dc_ancs,"
)

old = """
    html = template.substitute(
"""

new = """
    geography = {
        "counties": counties(),
        "municipalities": municipalities(),
        "dc_ancs": dc_ancs(),
    }

    html = template.substitute(
"""

if old in text:
    text = text.replace(old,new,1)

text = text.replace(
"""
        PARTIAL_ROUTES=f"{metrics['routes']['partially_verified_routes']:,}",
""",
"""
        PARTIAL_ROUTES=f"{metrics['routes']['partially_verified_routes']:,}",
        COUNTY_LIST=geography["counties"],
        MUNICIPALITY_LIST=geography["municipalities"],
        ANC_LIST=geography["dc_ancs"],
"""
)

p.write_text(text)

print("Added geography dashboard injection")
