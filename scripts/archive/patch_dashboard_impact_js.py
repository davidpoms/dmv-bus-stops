from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

js = p.read_text()


old = """        loadStops(
            this.value
        );

    }
);"""


new = """        loadStops(
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


if old not in js:
    raise SystemExit("Route listener block not found")


js = js.replace(old, new, 1)


p.write_text(js)

print("Added impact dropdown JS listener")
