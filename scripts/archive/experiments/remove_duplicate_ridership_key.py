from pathlib import Path
import shutil
from datetime import datetime

path = Path("src/api/app.py")

backup = path.with_suffix(
    path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)

shutil.copy(path, backup)

print("Backup:", backup)

text = path.read_text(encoding="utf-8")


duplicate = '''
            "ridership_exposure":
                ridership_exposure,

            
'''


if duplicate in text:
    text = text.replace(
        duplicate,
        "",
        1
    )
    print("Removed duplicate ridership exposure")
else:
    print("Duplicate block not found")


path.write_text(text, encoding="utf-8")

print("Complete")