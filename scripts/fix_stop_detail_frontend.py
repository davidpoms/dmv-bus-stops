from pathlib import Path

path = Path("src/dashboard/static/stop_detail.js")

text = path.read_text(encoding="utf-8")


# Fix broken checkmark encoding
text = text.replace(
    "âœ“ Confirmed present",
    "✓ Confirmed present"
)


# Fix route display ending if your current loop leaves names only
old = """                if (id && name) {

"""

new = """                if (id && name) {

"""


# no-op marker: route logic already exists
if old not in text:
    raise Exception("Expected route loop not found")


# Replace shelter source section with cleaner API-first wording
old = """            Primary source:

            ${
                stop.ddot_interpretation &&
                stop.ddot_interpretation.length
                ?

                stop.ddot_interpretation[0].source

                :

                "No verified source"
            }


        </div>
"""

new = """            Primary source:

            ${
                stop.ddot_interpretation &&
                stop.ddot_interpretation.length
                ?
                stop.ddot_interpretation[0].source
                :
                "No verified source"
            }


        </div>
"""

if old not in text:
    raise Exception("Primary source block not found")


text = text.replace(old,new)


# Replace evidence rendering section opening
old = """                          Confidence:

                      `
                  ).join("")
"""

new = """                          Confidence:
                          ${item.confidence || "unknown"}

                          <br>

                          Source ID:
                          ${item.source_record || "unknown"}

                          <br>

                          Routes:
                          ${
                            item.routes
                            ?
                            item.routes.join(", ")
                            :
                            "None"
                          }

                          </div>

                      `
                  ).join("")
"""

if old not in text:
    raise Exception("Evidence confidence block not found")


text = text.replace(old,new)


path.write_text(text, encoding="utf-8")

print("Fixed stop detail frontend")