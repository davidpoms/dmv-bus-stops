from pathlib import Path


path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


# Add import if missing
old_import = """
from src.assessment.interpretation import (
"""

if old_import in text and "interpret_ddot_evidence" not in text.split(old_import)[1].split(")")[0]:
    text = text.replace(
        old_import,
        old_import + "    interpret_ddot_evidence,\n"
    )


# Add function call after payload creation
marker = """
    wmata_history = get_wmata_history(stop_id)
"""

insert = """
    ddot_interpretation = interpret_ddot_evidence(
        ddot_evidence_payload
    )


    wmata_history = get_wmata_history(stop_id)
"""


if marker not in text:
    raise Exception(
        "Could not find API insertion point"
    )


text = text.replace(
    marker,
    insert
)


# Add response field
marker2 = """
            "ddot_evidence":
                ddot_evidence_payload,
"""

replacement2 = """
            "ddot_evidence":
                ddot_evidence_payload,

            "ddot_interpretation":
                ddot_interpretation,
"""


if marker2 not in text:
    raise Exception(
        "Could not find response field"
    )


text = text.replace(
    marker2,
    replacement2
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Added DDOT interpretation to stop API"
)