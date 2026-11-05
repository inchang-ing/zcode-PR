"""Compatibility entry point; pool data and discovery logic are shared."""
import sys

from repository_pools import load_pool
from scan_pool import api, scan, fetch, NOISE

CORE = load_pool("CORE", normalize=False)
WATCH = load_pool("WATCH", normalize=False)


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    which = sys.argv[2] if len(sys.argv) > 2 else "all"
    repos = {"core": CORE, "watch": WATCH, "all": CORE + WATCH}[which]
    scan(repos, hours, "agent " + which, workers=8, noise=NOISE, since=True)


if __name__ == "__main__":
    main()
