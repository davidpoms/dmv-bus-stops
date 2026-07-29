from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

text = text.replace(
    'function loadStops(route="", impact="") {',
    'function loadStops(route="", impact="", priority="") {'
)

old = """
    if (route) {
        url += "?route=" + route;

        if (impact) {
            url += "&impact=" + impact;
        }
    }

    else if (impact) {
        url += "?impact=" + impact;
    }
"""

new = """
    if (route) {
        url += "?route=" + route;

        if (impact) {
            url += "&impact=" + impact;
        }

        if (priority) {
            url += "&priority=" + priority;
        }
    }

    else if (impact) {
        url += "?impact=" + impact;

        if (priority) {
            url += "&priority=" + priority;
        }
    }

    else if (priority) {
        url += "?priority=" + priority;
    }
"""

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text)
    print("Updated loadStops priority support")
else:
    print("loadStops URL block not found")
