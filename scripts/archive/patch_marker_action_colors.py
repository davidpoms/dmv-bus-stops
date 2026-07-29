from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
                let color = "gray";
                let radius = 5;


                if (
                    props.validation_status === "validated"
                ) {
                    color = "red";
                    radius = 14;
                }

                else if (
                    props.validation_status === "needs_validation"
                ) {
                    color = "orange";
                    radius = 10;
                }
"""

new = """
                let color = "gray";
                let radius = 5;


                if (
                    props.action_status === "installed"
                ) {
                    color = "blue";
                    radius = 12;
                }

                else if (
                    props.action_status === "planned"
                ) {
                    color = "purple";
                    radius = 12;
                }

                else if (
                    props.validation_status === "validated"
                ) {
                    color = "green";
                    radius = 10;
                }

                else if (
                    props.validation_status === "needs_validation"
                ) {
                    color = "orange";
                    radius = 8;
                }
"""

if old not in text:
    print("marker color block not found")
    raise SystemExit(1)

text = text.replace(old, new)

p.write_text(text)

print("marker action colors patched")
