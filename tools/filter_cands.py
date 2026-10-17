#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only candidate summary using the pipeline's shared screening rules."""
import collections
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "tools"))
from auto_run import CANDIDATES, DispatchedStore, is_clean, load_candidates


def fresh_candidates(candidates, store):
    return [candidate for candidate in candidates if is_clean(candidate, store)[0]]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else CANDIDATES
    candidates = fresh_candidates(load_candidates(path), DispatchedStore())
    print("fresh clean candidates:", len(candidates))
    by_repo = collections.Counter(candidate.repo for candidate in candidates)
    have_source = {name[:-4] for name in os.listdir(BASE) if name.endswith("-src")}
    print("\n=== by repo (LOCAL-SRC = 本机有源码；测试能力需另行确认) ===")
    for repo, count in by_repo.most_common():
        tag = "LOCAL-SRC" if repo.split("/")[1] in have_source else ""
        print(f"  {repo:42s} {count:3d}  {tag}")
    print("\n=== 全部 fresh clean 候选清单（提交前仍须终检） ===")
    for candidate in candidates:
        print(f"  {candidate.repo}#{candidate.number:>6}  is_bug={candidate.is_bug}  "
              f"labels={candidate.labels}  {candidate.title[:70]}")


if __name__ == "__main__":
    main()
