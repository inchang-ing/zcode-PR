#!/usr/bin/env python
"""Push a local commit to a GitHub fork using the REST git data API.

Needed when the sandbox proxy kills git's https transport (CONNECT tunnel 502)
while api.github.com still works. Creates blobs -> tree -> commit -> ref.

Usage:
  python push_via_api.py <repo_dir> <owner/repo> <branch> <commit_sha>
"""
import base64
import json
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"


def gh_token() -> str:
    return subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=True
    ).stdout.strip()


def git(repo: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def git_raw(repo: str, *args: str) -> str:
    """Same as git() but keeps trailing whitespace/newlines (file contents need them)."""
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, check=True
    ).stdout


def api(method: str, path: str, token: str, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise SystemExit(f"HTTP {e.code} on {method} {path}: {body[:800]}")


def main() -> None:
    repo_dir, repo, branch, commit_sha = sys.argv[1:5]
    # Optional 5th arg: explicit parent sha (must exist on the remote). Use this
    # when the local repo has no history (e.g. built from a tarball) so we don't
    # need the parent as a local object.
    parent = sys.argv[5] if len(sys.argv) > 5 else git(repo_dir, "rev-parse", commit_sha + "^")
    token = gh_token()

    files = git(repo_dir, "show", "--name-only", "--pretty=format:", commit_sha).splitlines()
    files = [f.strip() for f in files if f.strip()]
    message = git(repo_dir, "log", "-1", "--format=%B", commit_sha)
    author_name = git(repo_dir, "log", "-1", "--format=%an", commit_sha)
    author_email = git(repo_dir, "log", "-1", "--format=%ae", commit_sha)
    author_date = git(repo_dir, "log", "-1", "--format=%aI", commit_sha)

    print(f"commit {commit_sha[:10]} parent {parent[:10]} files={files}")

    tree_entries = []
    for path in files:
        content = git_raw(repo_dir, "show", f"{commit_sha}:{path}")
        blob = api(
            "POST",
            f"/repos/{repo}/git/blobs",
            token,
            {
                "content": base64.b64encode(content.encode()).decode(),
                "encoding": "base64",
            },
        )
        mode = "100755" if git(repo_dir, "ls-files", "-s", "--", path).split()[0] == "100755" else "100644"
        tree_entries.append({"path": path, "mode": mode, "type": "blob", "sha": blob["sha"]})
        print(f"  blob {path} -> {blob['sha'][:10]}")

    base_tree = api("GET", f"/repos/{repo}/git/commits/{parent}", token)["tree"]["sha"]
    tree = api("POST", f"/repos/{repo}/git/trees", token, {"base_tree": base_tree, "tree": tree_entries})
    commit = api(
        "POST",
        f"/repos/{repo}/git/commits",
        token,
        {
            "message": message,
            "tree": tree["sha"],
            "parents": [parent],
            "author": {
                "name": author_name,
                "email": author_email,
                "date": author_date,
            },
        },
    )
    print(f"  new commit {commit['sha']}")

    try:
        api("POST", f"/repos/{repo}/git/refs", token, {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
        action = "created"
    except SystemExit:
        api("PATCH", f"/repos/{repo}/git/refs/heads/{branch}", token, {"sha": commit["sha"], "force": True})
        action = "updated"
    print(f"ref {branch} {action} -> {commit['sha']}")
    print(f"https://github.com/{repo}/tree/{branch}")


if __name__ == "__main__":
    main()
