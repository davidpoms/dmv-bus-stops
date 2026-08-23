from pathlib import Path
import re
import shutil
from datetime import datetime


path = Path("src/api/app.py")

backup = path.with_suffix(
    path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text(encoding="utf-8")


pattern = r'''
"wmata_evidence":\s*\(
\s*\{
\s*"status":\s*wmata_evidence\[0\]\[0\],
\s*"bench":\s*wmata_evidence\[0\]\[1\],
\s*"shelter":\s*wmata_evidence\[0\]\[2\],
\s*"accessible":\s*wmata_evidence\[0\]\[3\],
\s*"confidence":\s*wmata_evidence\[0\]\[4\],
\s*"distance_meters":\s*wmata_evidence\[0\]\[5\]
\s*\}
\s*if wmata_evidence
\s*else None
\s*\)
'''


replacement = '''
"wmata_evidence": wmata_evidence
'''


new_text, count = re.subn(
    pattern,
    replacement,
    text,
    flags=re.VERBOSE
)


print("Replacements:", count)


if count:
    path.write_text(new_text, encoding="utf-8")
    print("Fixed WMATA block")
else:
    print("No replacement made")