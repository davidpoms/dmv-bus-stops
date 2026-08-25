"""Direct/module-safe entry point for seating opportunity generation."""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.assessment.generate_seating_improvement_opportunities import (  # noqa: E402
    generate_opportunities,
)


if __name__ == "__main__":
    generate_opportunities(sys.argv[1] if len(sys.argv) > 1 else None)
