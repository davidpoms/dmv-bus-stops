from pathlib import Path


# Patch generated dashboard template
p = Path("src/dashboard/templates/dashboard.html")

if p.exists():
    text = p.read_text()

    old = """<select id="routeSelect">
<option value="">
All Routes
</option>
</select>
"""

    new = """<select id="routeSelect">
<option value="">
All Routes
</option>
</select>

<label>
Impact Filter:
</label>

<select id="impactSelect">
<option value="">
All Impacts
</option>

<option value="high">
High Impact+
</option>

<option value="very_high">
Very High Only
</option>
</select>

<div id="routeStatus">
Showing all routes
</div>
"""

    if old in text:
        text = text.replace(old, new)
        p.write_text(text)
        print("Patched dashboard template")
    else:
        print("Template block not found")
else:
    print("Template missing")


# Patch JS
p = Path("src/dashboard/static/dashboard.js")

js = p.read_text()

js = js.replace(
    'function loadStops(route="") {',
    'function loadStops(route="", impact="") {'
)

js = js.replace(
    """if (route) {
        url += "?route=" + route;
    }""",
    """if (route) {
        url += "?route=" + route;

        if (impact) {
            url += "&impact=" + impact;
        }
    }

    else if (impact) {
        url += "?impact=" + impact;
    }"""
)

old_listener = """document
.getElementById("routeSelect")
.addEventListener(
    "change",
    function() {

        loadStops(
            this.value
        );

    }
);"""


new_listener = """document
.getElementById("routeSelect")
.addEventListener(
    "change",
    function() {

        loadStops(
            this.value,
            document.getElementById("impactSelect").value
        );

    }
);


document
.getElementById("impactSelect")
.addEventListener(
    "change",
    function() {

        loadStops(
            document.getElementById("routeSelect").value,
            this.value
        );

    }
);"""


if old_listener in js:
    js = js.replace(old_listener, new_listener)
    print("Patched JS listeners")
else:
    print("Listener block not found")

p.write_text(js)
