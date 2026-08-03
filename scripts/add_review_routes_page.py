from pathlib import Path

APP = Path("src/api/app.py")
TEMPLATE = Path("src/dashboard/templates/review_routes.html")


template = """
<!DOCTYPE html>
<html>

<head>

<title>Choose My Routes</title>

<link rel="stylesheet" href="/static/dashboard.css">

</head>


<body>

<h1>
Choose Your Routes
</h1>


<div class="card volunteer-card">

<h2>
Help prioritize the stops you know best
</h2>

<p>
Select routes you ride, work on, or want to help improve.
Future reviews can prioritize stops along these routes.
</p>


<div id="routeList">

Loading routes...

</div>


<button
class="dashboard-button"
id="saveRoutes">

Save My Routes

</button>


<p id="routeStatus"></p>


</div>


<script>

async function loadRoutes(){

    const response = await fetch("/reviewer/routes");

    const data = await response.json();

    const container =
        document.getElementById("routeList");


    container.innerHTML = "";


    data.routes.forEach(route => {

        const checked =
            data.selected.includes(route.route_id)
            ? "checked"
            : "";


        container.innerHTML += `

        <label>
            <input
                type="checkbox"
                name="routes"
                value="${route.route_id}"
                ${checked}
            >

            ${route.route_id} - ${route.route_name}

        </label>

        <br>

        `;

    });

}


document
.getElementById("saveRoutes")
.addEventListener(
"click",
async function(){

    const routes =
        Array.from(
            document.querySelectorAll(
                'input[name="routes"]:checked'
            )
        )
        .map(
            box => box.value
        );


    await fetch(
        "/reviewer/routes",
        {
            method:"POST",

            headers:{
                "Content-Type":"application/json"
            },

            body:
                JSON.stringify({
                    routes: routes
                })
        }
    );


    document
    .getElementById("routeStatus")
    .innerText =
        "Routes saved!";

});


loadRoutes();

</script>


</body>

</html>
"""


if not TEMPLATE.exists():

    TEMPLATE.write_text(
        template,
        encoding="utf-8"
    )

    print("Created review_routes.html")

else:

    print("review_routes.html already exists")



text = APP.read_text(
    encoding="utf-8"
)


route = '''
@app.route("/review/routes")
def review_routes():

    return render_template(
        "review_routes.html"
    )

'''


if 'def review_routes()' not in text:

    marker = '@app.route("/dashboard")'

    text = text.replace(
        marker,
        route + "\\n\\n" + marker
    )

    APP.write_text(
        text,
        encoding="utf-8"
    )

    print("Added /review/routes Flask route")

else:

    print("/review/routes route already exists")