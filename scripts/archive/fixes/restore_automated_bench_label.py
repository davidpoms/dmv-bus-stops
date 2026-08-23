from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

text = text.replace(
    """
                                    Field observation - bench present:
                                    ${evidence.osm.osm_bench === 1 ? "Yes" : "No"}<br>
""",
    """
                                    Automated evidence - bench:
                                    ${evidence.osm.osm_bench === 1 ? "Yes" : "No"}<br>
"""
)

p.write_text(text)

print("Restored automated evidence label")
