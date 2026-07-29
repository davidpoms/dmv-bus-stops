from pathlib import Path

p = Path("src/dashboard/static/review_info_loader.js")

text = p.read_text()

old = """
                    ${
                        info.streetview_url
                        ?
                        `
                        <a href="${info.streetview_url}"
                           target="_blank">
                           Open Google Street View
                        </a>
                        `
                        :
                        ""
                    }
"""

new = """
                    ${
                        info.wmata
                        ?
                        `
                        <br><br>

                        <div class="evidence-card">

                            <strong>
                            WMATA Stop Inventory
                            </strong>

                            <br><br>

                            Shelter:
                            ${
                                info.wmata.shelter === "1"
                                ? "Yes"
                                : "No"
                            }

                            <br>

                            Bench:
                            ${
                                info.wmata.bench === "1"
                                ? "Yes"
                                : "No"
                            }

                            <br>

                            Accessible boarding:
                            ${
                                info.wmata.accessible === "Y"
                                ? "Yes"
                                : "No"
                            }

                            <br>

                            Match confidence:
                            ${
                                info.wmata.match_confidence || "Unknown"
                            }

                        </div>
                        `
                        :
                        ""
                    }


                    ${
                        info.streetview_url
                        ?
                        `
                        <br><br>

                        <a
                            href="${info.streetview_url}"
                            target="_blank"
                            class="stop-review-button">

                            Open Google Street View

                        </a>
                        `
                        :
                        ""
                    }
"""

if old not in text:
    raise Exception(
        "Could not find Street View block in review_info_loader.js"
    )

text = text.replace(old, new, 1)

needle = """
            const info =
                await response.json();
"""

replacement = """
            const info =
                await response.json();

            console.log(
                "Loaded review info:",
                info
            );
"""

if needle in text and "Loaded review info:" not in text:
    text = text.replace(
        needle,
        replacement,
        1
    )

p.write_text(text)

print(
    "Updated review_info_loader UI"
)
