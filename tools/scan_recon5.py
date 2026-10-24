#!/usr/bin/env python3
"""Recon pool D: another batch of high-profile projects not covered by
pools A/B/C. Avoids repos requiring a corporate CLA (Google/AWS/Microsoft/
Apache/IBM). Fresh open issues, no assignee, comments <= 2, super-fresh first."""
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta

GH = r"C:\Program Files\GitHub CLI\gh.exe"

POOL_D = [
    # scientific / data
    "scipy/scipy", "mwaskom/seaborn", "plotly/plotly.py", "modin-project/modin",
    "duckdb/duckdb", "holoviz/holoviews", "holoviz/hvplot", "pyvista/pyvista",
    "sympy/sympy", "huggingface/datasets", "nltk/nltk", "explosion/spaCy",
    "RaRe-Technologies/gensim", "dmlc/xgboost", "ray-project/ray",
    # web frameworks / servers
    "bottlepy/bottle", "Pylons/pyramid", "tornadoweb/tornado",
    "benoitc/gunicorn", "Supervisor/supervisor", "pallets/itsdangerous",
    "pallets/blinker", "aio-libs/yarl", "aio-libs/multidict",
    # CLI / UI
    "prompt-toolkit/python-prompt-toolkit", "sdispater/cleo",
    "zauberzeug/nicegui", "flet-dev/flet", "reflex-dev/reflex",
    "pyinvoke/invoke", "fabric/fabric", "paramiko/paramiko",
    "cookiecutter/cookiecutter", "copier-org/copier",
    # testing / quality
    "nedbat/coveragepy", "behave/behave", "robotframework/robotframework",
    "locustio/locust", "pytest-dev/pytest-cov", "pytest-dev/pytest-timeout",
    "ionelmc/pytest-benchmark", "pytest-dev/pytest-rerunfailures",
    # packaging / tooling
    "pypa/pipx", "pypa/virtualenv", "pypa/packaging", "pypa/wheel",
    "python-lsp/python-lsp-server", "PyJWT/jwt", "python-attrs/cattrs",
    "boto/boto3", "localstack/localstack", "httpie/httpie",
    # infra / devops / misc
    "ansible/ansible", "dbt-labs/dbt-core", "yt-dlp/yt-dlp",
    "huggingface/transformers", "jupyter/notebook", "jupyterlab/jupyterlab",
    "spyder-ide/spyder", "python-pillow/Pillow", "imageio/imageio",
    "python-opencv/opencv-python",
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
        data = api(f"repos/{repo}/issues?state=open&sort=created&direction=desc&per_page=25")
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
        tag = "SUPER" if age <= 6 else ("fresh" if age <= 24 else "48h")
        print(f"{tag:6} {age:5.1f}h c={cm} {repo}#{num} [{labels}] {title}")
    return out


if __name__ == "__main__":
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    scan(POOL_D, hours, "POOL-D")
