"""Fresh-process private runtime check; never loads WSGI or database files."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.api.sqlite_runtime import load_production_sqlite, inspect_loaded_sqlite


if __name__ == '__main__':
    load_production_sqlite()
    print(json.dumps(inspect_loaded_sqlite(), sort_keys=True))
