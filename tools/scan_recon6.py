"""Compatibility entry point; pool data and discovery logic are shared."""
import sys

from repository_pools import load_pool
from scan_pool import api, scan, fetch, NOISE

POOL_E = load_pool("POOL_E", normalize=False)


def main():
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 96
    scan(POOL_E, hours, "POOL_E", per_page=20)


if __name__ == "__main__":
    main()
