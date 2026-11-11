"""Print non-secret SQLite capabilities using only an in-memory database."""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.review.recognition.sqlite_capabilities import inspect_runtime


if __name__ == '__main__':
    print(json.dumps(inspect_runtime(), sort_keys=True))
