"""Pure repository-pool loading; membership belongs to each discovery lane.

Reading pool data never imports or executes a scanner. Manual contribution
restrictions remain observable; hard bans and untestable repos are excluded
from broad monitoring exactly as before.
"""
import json
from pathlib import Path

from repository_policy import BLOCKED_OWNERS, BLOCKED_REPOS, DEAD_OR_RENAMED, NON_TESTABLE

POOL_DATA = Path(__file__).with_suffix(".json")


def normalize_repo(repo, *, exclude_restricted=True):
    if not isinstance(repo, str):
        raise ValueError("repository pool entry must be a string")
    repo = repo.strip().rstrip("?").lower()
    if not repo or "/skip" in repo:
        return None
    repo = DEAD_OR_RENAMED.get(repo, repo)
    if repo is None:
        return None
    if len(repo.split("/")) != 2 or any(not part for part in repo.split("/")):
        raise ValueError(f"invalid repository pool entry: {repo!r}")
    if exclude_restricted and (repo in BLOCKED_REPOS or repo in NON_TESTABLE
                               or repo.split("/", 1)[0] in BLOCKED_OWNERS):
        return None
    return repo


def normalize_repos(repos, *, exclude_restricted=True):
    result, seen = [], set()
    for raw in repos:
        repo = normalize_repo(raw, exclude_restricted=exclude_restricted)
        if repo and repo not in seen:
            result.append(repo)
            seen.add(repo)
    return result


def load_pool(name, *, normalize=True):
    data = json.loads(POOL_DATA.read_text(encoding="utf-8"))
    repos = data[name]
    if not isinstance(repos, list) or any(not isinstance(repo, str) for repo in repos):
        raise ValueError(f"invalid pool: {name}")
    return normalize_repos(repos) if normalize else list(repos)


def load_pool_file(path):
    """Load a lane's existing JSON string list without expanding its scope."""
    repos = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(repos, list):
        raise ValueError("repository pool must be a list")
    return normalize_repos(repos)


def load_quality_pool(path):
    """Normalize the focused pool while retaining its metadata and exclusions.

    Repository gates run against live issue labels/assignees in the callers;
    this loader must not turn pool-specific exclusions into global policy.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("watch"), list):
        raise ValueError("focused repository pool must contain a watch list")
    watch, positions = [], {}
    for raw in data["watch"]:
        item = {"repo": raw} if isinstance(raw, str) else dict(raw)
        repo = normalize_repo(item.get("repo"), exclude_restricted=False)
        if repo is None:
            continue
        if repo not in positions:
            positions[repo] = len(watch)
            watch.append({**item, "repo": repo})
        else:
            previous = watch[positions[repo]]
            for flag in ("heavy", "rust"):
                if item.get(flag):
                    previous[flag] = True
    blocked = data.get("blocked", {})
    if not isinstance(blocked, dict) or not isinstance(blocked.get("repos", []), list):
        raise ValueError("focused repository exclusions must be a list")
    return {**data, "watch": watch, "blocked": {**blocked, "repos":
        normalize_repos(blocked.get("repos", []), exclude_restricted=False)}}


def build_tiers():
    """Return (always, rotating), preserving fastest-tier precedence and order."""
    data = json.loads(POOL_DATA.read_text(encoding="utf-8"))
    def combined(names):
        repos = []
        for name in names:
            if not isinstance(data[name], list):
                raise ValueError(f"invalid pool: {name}")
            repos.extend(data[name])
        return normalize_repos(repos)
    always = combined(("CORE", "WATCH", "G"))
    rotating = combined(("MAIN_POOL", "EXTENSION_POOL", "NEW_POOL", "POOL_B", "POOL_C", "POOL_D", "POOL_E"))
    seen = set(always)
    return always, [repo for repo in rotating if repo not in seen]
