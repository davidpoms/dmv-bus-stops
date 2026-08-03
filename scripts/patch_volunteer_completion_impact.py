from pathlib import Path

app_path = Path("src/api/app.py")
review_path = Path("src/dashboard/templates/review.html")


# ----------------------------
# Patch API response
# ----------------------------

app_text = app_path.read_text(encoding="utf-8")

old_api = '''        "community_impact": {
            "daily_route_exposure":
                impact[0][0]
                if impact
                else None
        }
'''

new_api = '''        "community_impact": {
            "daily_route_exposure":
                impact[0][0]
                if impact
                else None,

            "routes":
                ridership_exposure["routes"]
                if ridership_exposure
                else []
        }
'''

if old_api not in app_text:
    raise RuntimeError(
        "Could not find community_impact block in app.py"
    )

app_text = app_text.replace(
    old_api,
    new_api
)

app_path.write_text(
    app_text,
    encoding="utf-8"
)

print("Updated review submit community impact response.")


# ----------------------------
# Patch completion card
# ----------------------------

review_text = review_path.read_text(encoding="utf-8")


old_card = '''<p>
This stop serves approximately
<strong>
${
    result.community_impact.daily_route_exposure
    ? result.community_impact.daily_route_exposure.toLocaleString()
    : "unknown"
}
</strong>
daily riders through the routes serving it.
</p>


${
    result.reviewer_stats.first_review
    ?
    `
    <p>
    ⭐ You were the first community reviewer for this stop.
    </p>
    `
    :
    ""
}
'''

new_card = '''<p>
Your review helped validate a stop serving approximately
<strong>
${
    result.community_impact.daily_route_exposure
    ?
    Math.round(
        result.community_impact.daily_route_exposure
    ).toLocaleString()
    :
    "unknown"
}
</strong>
weekday riders.
</p>


${
    result.community_impact.routes &&
    result.community_impact.routes.length
    ?
    `
    <p>
    Route(s):
    <strong>
    ${result.community_impact.routes.join(", ")}
    </strong>
    </p>
    `
    :
    ""
}


${
    result.reviewer_stats.first_review
    ?
    `
    <p>
    ⭐ You established the first community record for this stop.
    </p>
    `
    :
    ""
}
'''

if old_card not in review_text:
    raise RuntimeError(
        "Could not find completion card block in review.html"
    )

review_text = review_text.replace(
    old_card,
    new_card
)

review_path.write_text(
    review_text,
    encoding="utf-8"
)

print("Updated volunteer completion card.")