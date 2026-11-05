"""Compatibility entry point; pool data and discovery logic are shared."""
import sys

from repository_pools import load_pool
from scan_pool import api, scan, fetch, NOISE

NEW_POOL = load_pool("NEW_POOL", normalize=False)
MAIN_POOL = load_pool("MAIN_POOL", normalize=False)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "new"
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    scan(NEW_POOL if which == "new" else MAIN_POOL, hours, which.upper())


if __name__ == "__main__":
    main()
