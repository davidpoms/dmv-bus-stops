"""Explicit additive recognition migration. No default database target."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.review.recognition.schema import migrate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="Install schema only; does not enable recognition")
    args = parser.parse_args(argv)
    migrate(args.db, apply=args.apply)
    print("Recognition schema installed; capture/issuance remain disabled." if args.apply
          else "Recognition migration rehearsal passed; target database unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
