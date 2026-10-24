#!/usr/bin/env python3
"""Extended recon scan over high-profile repos: fresh open issues, no assignee,
comments <= 2, sorted by age (super-fresh first)."""
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta

GH = r"C:\Program Files\GitHub CLI\gh.exe"

# New high-profile pool (Python ecosystem + a few cross-language infra)
NEW_POOL = [
    "fastapi/fastapi", "pydantic/pydantic", "encode/httpx", "encode/starlette",
    "encode/uvicorn", "encode/django-rest-framework", "django/django",
    "pandas-dev/pandas", "numpy/numpy", "pola-rs/polars", "matplotlib/matplotlib",
    "scikit-learn/scikit-learn", "pre-commit/pre-commit", "tox-dev/tox",
    "wntrblm/nox", "pypa/hatch", "pdm-project/pdm", "Textualize/rich",
    "marshmallow-code/marshmallow", "jcrist/msgspec", "ijl/orjson",
    "dask/dask", "apache/airflow", "PrefectHQ/prefect", "dagster-io/dagster",
    "mlflow/mlflow", "iterative/dvc", "facebookresearch/hydra", "omry/omegaconf",
    "great-expectations/great_expectations", "unionai-oss/pandera",
    "streamlit/streamlit", "gradio-app/gradio", "plotly/dash", "bokeh/bokeh",
    "altair-viz/altair", "litestar-org/litestar", "sanic-org/sanic",
    "rq/rq", "Bogdanp/dramatiq", "coleifer/huey", "sphinx-doc/sphinx",
    "pypa/twine", "conda/conda", "optuna/optuna", "kedro-org/kedro",
    "home-assistant/core", "python-telegram-bot/python-telegram-bot",
    "wagtail/wagtail", "frappe/frappe", "apache/superset", "getmoto/moto",
    "pytest-dev/pytest-xdist", "pytest-dev/pytest-mock", "pytest-dev/pytest-asyncio",
    "aio-libs/aiosignal", "aio-libs/aiohttp-cors", "aio-libs/janus",
    "omnilib/aiosqlite", "aio-libs/aiomysql", "aio-libs/aioredis-py",
]

MAIN_POOL = [
    "pytest-dev/pytest", "pylint-dev/pylint", "pylint-dev/astroid", "celery/celery",
    "scrapy/scrapy", "psf/black", "python-poetry/poetry", "sqlalchemy/sqlalchemy",
    "mitmproxy/mitmproxy", "PyGithub/PyGithub", "urllib3/urllib3", "certbot/certbot",
    "aiohttp-libs/aiohttp", "tqdm/tqdm", "networkx/networkx", "psf/requests",
    "jd/tenacity", "ipython/ipython", "redis/redis-py", "pypa/setuptools",
    "strawberry-graphql/strawberry", "python/mypy", "python-attrs/attrs",
    "python-websockets/websockets", "fastapi/typer", "elastic/elasticsearch-py",
    "agronholm/anyio", "sqlalchemy/alembic", "agronholm/apscheduler",
    "Python-Markdown/markdown", "psycopg/psycopg2", "tobymao/sqlglot",
    "PyCQA/pydocstyle", "PyCQA/astroid", "python-jsonschema/jsonschema",
    "PyCQA/pycodestyle", "PyCQA/pyflakes", "more-itertools/more-itertools",
    "pypa/build", "pytest-dev/pluggy", "pytest-dev/execnet",
    "executablebooks/markdown-it-py", "yaml/pyyaml", "Textualize/textual",
    "python-poetry/tomlkit", "pypa/pip", "pallets/werkzeug", "jaraco/skeleton",
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
            print(f"[skip] {repo}")
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
    which = sys.argv[1] if len(sys.argv) > 1 else "new"
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    scan(NEW_POOL if which == "new" else MAIN_POOL, hours, which.upper())
