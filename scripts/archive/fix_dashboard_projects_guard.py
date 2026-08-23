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
                                if (detail.projects.length > 0) {

                                    detail.projects.forEach(
                                        project => {

                                            popup +=
                                            `${project.recommendation}: ${project.status}<br>`;

                                        }
                                    );

                                }
"""


new = """
                                if (detail.projects && detail.projects.length > 0) {

                                    detail.projects.forEach(
                                        project => {

                                            popup +=
                                            `${project.recommendation}: ${project.status}<br>`;

                                        }
                                    );

                                }
"""


if old in text:
    text = text.replace(old, new)
    print("Fixed projects guard")
else:
    print("Could not find exact projects block")


path.write_text(text, encoding="utf-8")

print("Complete")