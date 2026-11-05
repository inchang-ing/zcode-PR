"""Compatibility entry point; pool data and discovery logic are shared."""
import sys

from repository_pools import load_pool
from scan_pool import api, scan, fetch, NOISE

POOL_D = load_pool("POOL_D", normalize=False)


def main():
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    scan(POOL_D, hours, "POOL_D")


if __name__ == "__main__":
    main()
