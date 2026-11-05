"""Compatibility entry point; pool data and discovery logic are shared."""
import sys

from repository_pools import load_pool
from scan_pool import api, scan, fetch, NOISE

G = load_pool("G", normalize=False)


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    scan(G, hours, "agent G", workers=8, noise=NOISE, since=True)


if __name__ == "__main__":
    main()
