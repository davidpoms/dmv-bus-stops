from pathlib import Path
import shutil
from datetime import datetime

path = Path("src/dashboard/static/dashboard.js")

backup = path.with_suffix(
    path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)

shutil.copy(path, backup)

print("Backup:", backup)

text = path.read_text(encoding="utf-8")


old = """
                        detail.ridership_exposure &&
                        
                        detail.ridership_exposure.routes.length
                        ?
                        detail.ridership_exposure.routes.join(", ")
                        :
                        "Unknown"
"""


new = """
                        detail.ridership_exposure &&
                        detail.ridership_exposure.routes &&
                        detail.ridership_exposure.routes.length
                        ?
                        detail.ridership_exposure.routes.join(", ")
                        :
                        "Unknown"
"""


if old in text:
    text = text.replace(old, new)
    print("Fixed ridership routes guard")
else:
    print("Could not find exact ridership block")


path.write_text(text, encoding="utf-8")

print("Complete")