from pathlib import Path


APP = Path("src/api/app.py")
HTML = Path("src/dashboard/templates/dashboard.html")


def insert_routes_api(text):

    marker = '@app.route("/routes")'

    insert = r'''

@app.route("/reviewer/routes")
def reviewer_routes():

    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    routes = query_db(
        """
        SELECT
            route_id,
            route_name

        FROM routes

        ORDER BY route_id
        """
    )


    selected = query_db(
        """
        SELECT route_id

        FROM community_reviewer_routes

        WHERE reviewer_id=?
        """,
        (
            reviewer_id,
        )
    )


    return jsonify(
        {
            "routes":
                [
                    {
                        "route_id": r[0],
                        "route_name": r[1]
                    }
                    for r in routes
                ],

            "selected":
                [
                    r[0]
                    for r in selected
                ]
        }
    )



@app.route(
    "/reviewer/routes",
    methods=["POST"]
)
def save_reviewer_routes():

    data = request.get_json()

    reviewer_key = session.get(
        "reviewer_key"
    )

    reviewer_id, reviewer_key = get_or_create_reviewer(
        reviewer_key
    )

    session["reviewer_key"] = reviewer_key


    routes = data.get(
        "routes",
        []
    )


    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cur = conn.cursor()


    cur.execute(
        """
        DELETE FROM community_reviewer_routes

        WHERE reviewer_id=?
        """,
        (
            reviewer_id,
        )
    )


    for route in routes:

        cur.execute(
            """
            INSERT INTO community_reviewer_routes
            (
                reviewer_id,
                route_id
            )

            VALUES (?,?)
            """,
            (
                reviewer_id,
                route
            )
        )


    conn.commit()
    conn.close()


    return jsonify(
        {
            "success": True,
            "routes": routes
        }
    )


'''

    if "/reviewer/routes" in text:
        return text

    return text.replace(
        marker,
        insert + "\n" + marker
    )


def insert_dashboard_button(text):

    marker = '<div class="review-options">'

    addition = r'''

<div class="review-option">

<a href="/review/routes">
🚌 Choose My Routes
</a>

<p>
Select the routes you ride or steward so reviews can prioritize those stops.
</p>

</div>

<div class="review-option">

<a href="/review/start?mode=route">
🚌 My Routes
</a>

<p>
Review stops along your selected routes.
</p>

</div>

'''

    if "Choose My Routes" in text:
        return text

    return text.replace(
        marker,
        marker + addition
    )


app_text = APP.read_text(
    encoding="utf-8"
)

app_text = insert_routes_api(
    app_text
)

APP.write_text(
    app_text,
    encoding="utf-8"
)


html_text = HTML.read_text(
    encoding="utf-8"
)

html_text = insert_dashboard_button(
    html_text
)

HTML.write_text(
    html_text,
    encoding="utf-8"
)


print(
    "Added reviewer route preference endpoints and dashboard links"
)