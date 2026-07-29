from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

needle = """
    markers = [];
"""

insert = """
    const legend =
        L.control({position: "bottomright"});


    legend.onAdd = function() {

        const div =
            L.DomUtil.create(
                "div",
                "mapLegend"
            );


        div.innerHTML = `
            <b>Community Status</b><br>
            <span style="color:blue">●</span>
            Installed improvement<br>

            <span style="color:purple">●</span>
            Planned action<br>

            <span style="color:green">●</span>
            Validated stop<br>

            <span style="color:orange">●</span>
            Needs validation
        `;


        return div;
    };


    legend.addTo(map);


    markers = [];
"""

if needle not in text:
    print("marker initialization not found")
    raise SystemExit(1)

text = text.replace(
    needle,
    insert,
    1
)

p.write_text(text)

print("map legend added")
