from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

marker = """
loadStops();
"""

insert = """
document
.getElementById("prioritySelect")
.addEventListener(
    "change",
    function() {

        const priority = this.value;

        loadStops(
            "",
            priority
        );

    }
);


"""

if marker in text:
    text = text.replace(marker, insert + marker, 1)
    p.write_text(text)
    print("Added priority listener")
else:
    print("loadStops marker not found")
