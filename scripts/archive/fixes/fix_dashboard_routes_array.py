from pathlib import Path

path = Path("src/dashboard/static/dashboard.js")

text = path.read_text(encoding="utf-8")


old = """
Routes:
                                ${
                                    detail.impact_summary &&
                                    detail.impact_summary.routes &&
                                    detail.impact_summary.routes.length
                                    ? detail.impact_summary.routes.join(", ")
                                    : "Unknown"
                                }
"""


new = """
Routes:
                                ${
                                    detail.impact_summary &&
                                    Array.isArray(detail.impact_summary.routes) &&
                                    detail.impact_summary.routes.length
                                    ? detail.impact_summary.routes.join(", ")
                                    : "Unknown"
                                }
"""


if old not in text:
    print("Could not find routes popup block")
else:
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print("Updated dashboard route rendering")


print("dashboard.js patch complete")