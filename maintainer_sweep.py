"""Sweep allowed repos for maintainer-filed, unfixed bug issues (5-45d old)."""
import json
import subprocess
from datetime import datetime, timedelta, timezone

GH = "C:/Program Files/GitHub CLI/gh.exe"
NOW = datetime.now(timezone.utc)
# allowed by org probe, not in blocked list, in-flight < 2, no AI ban known
REPOS = [
    "fastapi/fastapi", "tiangolo/typer", "python-attrs/attrs", "aio-libs/anyio",
    "pytest-dev/pluggy", "frankie567/keyring", "psycopg/psycopg", "sqlalchemy/alembic",
    "python-poetry/poetry", "redis/redis-py", "urllib3/urllib3", "strawberry-graphql/strawberry",
    "python/mypy", "PyGithub/PyGithub", "pypa/build", "statsmodels/statsmodels",
    "docling-project/docling", "Arize-ai/openinference", "aio-libs/aiohttp",
]

def gh(args):
    r = subprocess.run([GH] + args, capture_output=True, text=True, timeout=90)
    if r.returncode:
        return None
    return json.loads(r.stdout)

for repo in REPOS:
    issues = gh(["api", f"repos/{repo}/issues?state=open&sort=created&direction=desc&per_page=100"])
    if not isinstance(issues, list):
        print(f"SKIP {repo}")
        continue
    for it in issues:
        if "pull_request" in it:
            continue
        created = datetime.fromisoformat(it["created_at"].replace("Z", "+00:00"))
        age_days = (NOW - created).days
        if not 5 <= age_days <= 45:
            continue
        labels = [l["name"] for l in it.get("labels", [])]
        if not any(l in ("bug", "type:bug", "Bug", "confirmed", "type: bug") for l in labels):
            continue
        assoc = it.get("author_association", "NONE")
        if assoc not in ("MEMBER", "OWNER", "COLLABORATOR"):
            continue
        print(f"{repo}#{it['number']} [{assoc},{age_days}d,{it['comments']}c,{','.join(labels)}] {it['title'][:90]}")
