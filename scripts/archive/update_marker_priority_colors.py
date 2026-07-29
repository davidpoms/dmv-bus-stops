from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
                let color = "gray";
                let radius = 5;


                if (
                    props.impact === "very_high"
                ) {
                    color = "red";
                    radius = 14;
                }

                else if (
                    props.impact === "high"
                ) {
                    color = "orange";
                    radius = 10;
                }

                else if (
                    props.impact === "medium"
                ) {
                    color = "gold";
                    radius = 7;
                }
"""

new = """
                let color = "gray";
                let radius = 5;


                if (
                    props.priority === "P1"
                ) {
                    color = "red";
                    radius = 14;
                }

                else if (
                    props.priority === "P2"
                ) {
                    color = "orange";
                    radius = 10;
                }

                else if (
                    props.priority === "P3"
                ) {
                    color = "gold";
                    radius = 7;
                }
"""

if old in text:
    text = text.replace(old, new, 1)
else:
    print("Marker color block not found")

text = text.replace(
"""props.impact === "very_high"
                            ? "veryHighPriority"
                            :
                            props.impact === "high"
                            ? "highPriority"
                            :
                            "markerPane""",
"""props.priority === "P1"
                            ? "veryHighPriority"
                            :
                            props.priority === "P2"
                            ? "highPriority"
                            :
                            "markerPane"""
)

text = text.replace(
"""props.impact === "very_high" ||
                    props.impact === "high""",
"""props.priority === "P1" ||
                    props.priority === "P2"""
)

text = text.replace(
"""Impact: ${props.impact}<br><br>""",
"""Priority: ${props.priority}<br>
                                Impact: ${props.impact}<br><br>"""
)

p.write_text(text)

print("Updated markers to priority styling")
