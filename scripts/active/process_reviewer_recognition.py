"""Read-only global recognition backfill planning; no apply/enable mode."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.review.recognition.backfill import dry_run
from src.review.recognition.rules import canonical


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--rule-key", required=True)
    parser.add_argument("--through-assignment", type=int, required=True)
    parser.add_argument("--after-assignment", type=int, default=0)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--sqlite-utc-provenance", help="Reviewed generating-path provenance reference, never a guess")
    args = parser.parse_args(argv)
    print(canonical(dry_run(args.db, args.rule_key, through_assignment=args.through_assignment,
                            after_assignment=args.after_assignment, limit=args.limit,
                            sqlite_utc_provenance=args.sqlite_utc_provenance)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
