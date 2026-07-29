from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
                if (
                    props.priority === "P1"
                ) {

                    marker.setStyle({
                        color: "red"
                    });

                }

                else if (
                    props.priority === "P2"
                ) {

                    marker.setStyle({
                        color: "orange"
                    });

                }

                else if (
                    props.priority === "P3"
                ) {

                    marker.setStyle({
                        color: "gold"
                    });

                }
"""


new = """
                if (
                    props.validation_status === "validated"
                ) {

                    marker.setStyle({
                        color: "green"
                    });

                }

                else if (
                    props.validation_status === "needs_validation"
                ) {

                    marker.setStyle({
                        color: "gray"
                    });

                }

                else {

                    marker.setStyle({
                        color: "orange"
                    });

                }
"""


if old not in text:
    print("marker priority block not found")
    raise SystemExit(1)


text = text.replace(
    old,
    new
)


# Remove old priority bring-to-front behavior
text = text.replace(
"""
                if (
                    props.priority === "P1" ||
                    props.priority === "P2"
                ) {

                    marker.bringToFront();

                }
""",
"""
                if (
                    props.validation_status === "validated"
                ) {

                    marker.bringToFront();

                }
"""
)


p.write_text(text)

print("marker validation styling patched")

