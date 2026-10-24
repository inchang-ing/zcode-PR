#!/usr/bin/env python3
"""Pool E: LOW-COMPETITION repos (jaraco/*, PyCQA/*, psf/*, pypa/*, and other
small-but-known libraries). Rationale: on high-profile repos, AI agents claim
fresh issues within ~1h (8 collisions observed in one round), so the expected
value of scanning cold repos is higher. Wider window (default 96h) is fine
because competition is low there."""
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta

GH = r"C:\Program Files\GitHub CLI\gh.exe"

POOL_E = [
    # jaraco ecosystem (maintained, low traffic)
    "jaraco/skeleton", "jaraco/inflect", "jaraco/jaraco.context",
    "jaraco/jaraco.functools", "jaraco/jaraco.text", "jaraco/jaraco.classes",
    "jaraco/jaraco.logging", "jaraco/jaraco.itertools",
    "jaraco/keyring", "jaraco/zipp", "jaraco/tempora", "jaraco/portend",
    # PyCQA / psf linters & tooling
    "PyCQA/pydocstyle", "PyCQA/flake8", "PyCQA/bandit", "PyCQA/isort",
    "psf/pycodestyle", "PyCQA/pyflakes", "psf/requests-html", "psf/cachecontrol",
    # pypa
    "pypa/build", "pypa/distutils", "pypa/pipenv", "pypa/installer",
    "pypa/cibuildwheel", "pypa/pyproject-hooks", "pypa/readme_renderer",
    # pytest-dev satellites
    "pytest-dev/pluggy", "pytest-dev/execnet", "pytest-dev/pytest-bdd",
    "pytest-dev/pytest-forked", "pytest-dev/pytest-lazy-fixture",
    # small stdlib-adjacent utilities (well known, low issue traffic)
    "dateutil/dateutil", "benjaminp/six", "mahmoud/boltons", "Suor/funcy",
    "pytoolz/toolz", "tobgu/pyrsistent", "jab/bidict", "python-babel/babel",
    "pallets/markupsafe", "pallets/itsdangerous", "GrahamDumpleton/wrapt",
    "python-jsonschema/jsonschema", "more-itertools/more-itertools",
    "aio-libs/async-timeout", "seddonym/import-linter", "boltons/boltons",
    "Textualize/trogon", "pydantic/pydantic-settings", "encode/databases",
    "encode/broadcaster", "encode/httpcore", "encode/httpx-ws",
]


def api(path):
    r = subprocess.run([GH, "api", path], capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def scan(repos, max_age_h, label):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max_age_h)
    out = []
    for repo in repos:
        data = api(f"repos/{repo}/issues?state=open&sort=created&direction=desc&per_page=20")
        if data is None:
            print(f"[skip] {repo}", flush=True)
            continue
        for it in data:
            if it.get("pull_request"):
                continue
            created = datetime.fromisoformat(it["created_at"].replace("Z", "+00:00"))
            if created < cutoff:
                continue
            if it.get("assignee") or it.get("assignees"):
                continue
            if it.get("comments", 0) > 2:
                continue
            age_h = (now - created).total_seconds() / 3600
            labels = ",".join(l.get("name", "") for l in it.get("labels", []))
            out.append((repo, it["number"], round(age_h, 1), it.get("comments", 0),
                        labels, it["title"][:110]))
        print(f"[ok] {repo}", flush=True)
    out.sort(key=lambda x: x[2])
    print(f"\n===== {label}: {len(out)} candidates (<= {max_age_h}h) =====")
    for repo, num, age, cm, labels, title in out:
        tag = "SUPER" if age <= 6 else ("fresh" if age <= 24 else "old")
        print(f"{tag:6} {age:5.1f}h c={cm} {repo}#{num} [{labels}] {title}")
    return out


if __name__ == "__main__":
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 96
    scan(POOL_E, hours, "POOL-E")
