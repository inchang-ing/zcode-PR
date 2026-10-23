"""Compatibility entry point; implementation and pool live in tools/."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from scan_candidates import main

if __name__ == "__main__":
    sys.exit(main())
