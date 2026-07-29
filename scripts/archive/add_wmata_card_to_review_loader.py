from pathlib import Path

FILE = Path("src/dashboard/static/review_info_loader.js")

text = FILE.read_text()

old = """
                    Jurisdiction:
                    ${info.state || ""}
                    ${info.county ? " | " + info.county : ""}
                    ${info.municipality ? " | " + info.municipality : ""}

                    <br><br>

                    ${
                        info.streetview_url
"""

new = """
                    Jurisdiction:
                    ${info.state || ""}
                    ${info.county ? " | " + info.county : ""}
                    ${info.municipality ? " | " + info.municipality : ""}

                    <br><br>

                    ${
                        info.wmata
                        ?
                        `
                        <div class="evidence-card">

                            <strong>
                            WMATA Transit Information
                            </strong>

                            <br><br>

                            WMATA Stop ID:
                            ${info.wmata.stop_id || "Unknown"}

                            <br>

                            Status:
                            ${
                                info.wmata.status === "PRS"
                                ? "Published stop"
                                : (info.wmata.status || "Unknown")
                            }

                            <br>

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

                            Accessible:
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

                        <br>
                        `
                        :
                        ""
                    }

                    ${
                        info.streetview_url
"""

if old not in text:
    raise Exception("Could not find insertion point")

text = text.replace(old, new)

FILE.write_text(text)

print("Added WMATA card to review loader")
