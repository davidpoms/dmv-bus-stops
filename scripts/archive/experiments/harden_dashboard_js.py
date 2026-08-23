from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


replacements = {

"""
document
.getElementById("routeSelect")
.addEventListener(
    "change",
    function() {

        loadStops(
            this.value
        );

    }
);
""":
"""
const routeSelect = document.getElementById("routeSelect");

if(routeSelect){

    routeSelect.addEventListener(
        "change",
        function(){

            loadStops(
                this.value
            );

        }
    );

}
""",


"""
loadStops();
""":
"""
if(document.getElementById("map")){
    loadStops();
}
"""

}


for old,new in replacements.items():

    if old in text:
        text=text.replace(old,new)
        print("Patched JS block")
    else:
        print("Block not found")


p.write_text(text)

print("Dashboard JS hardened")
