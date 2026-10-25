"""Scan the focused repository pool; incomplete checks are UNKNOWN, never CLEAN.

Usage: python tools/scan_candidates.py [--days 2] [--max 6]
Output: work/ledger/candidates.json (a separate screening report).
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import time

from claim_rules import SOFT, NOT_READY
from gh_checks import comment_bodies, linked_prs, paginated_items, issue_errors
from pipeline_state import atomic_write_json, file_lock, read_json_object
from pr_state import load_pr_state
from repository_policy import policy_reason

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "tools/quality_repos.json"
LEDGER = ROOT / "work/ledger/pr_states.json"
OUT = ROOT / "work/ledger/candidates.json"
FIXED_IN_PR = re.compile(
    "|".join(re.escape(p) for p in (
        "fixed by pr", "fixed by #", "resolved by pr", "resolved by #",
        "fixed in pr", "fix reference", "already fixed", "pr that fixes"))
    + r"|(?:pr|pull request) #\d+ fixes\b|(?<![\w/#])#\d+ fixes\b", re.IGNORECASE)
ISSUE_REFERENCE = re.compile(
    r"(?P<url>https?://[^\s<>()\[\]]+)|"
    r"(?<![\w/.-])(?:(?P<repo>[\w.-]+/[\w.-]+))?#(?P<number>\d+)\b", re.IGNORECASE)
ISSUE_URL = re.compile(
    r"https?://github\.com/(?P<repo>[\w.-]+/[\w.-]+)/issues/(?P<number>\d+)"
    r"(?:[/?#].*)?", re.IGNORECASE)


def issue_references(text, repo):
    """Only references to this repository can collide with its candidates."""
    numbers = set()
    for match in ISSUE_REFERENCE.finditer(text):
        if match["url"]:
            # Consume complete URLs so their fragments cannot become bare #N refs.
            match = ISSUE_URL.fullmatch(match["url"].rstrip(".,;:!`'\""))
            if match is None:
                continue
        if match["repo"] is None or match["repo"].lower() == repo.lower():
            numbers.add(int(match["number"]))
    return numbers


def gh(*args):
    try:
        result = subprocess.run(["gh", "api", *args], capture_output=True,
                                text=True, encoding="utf-8", timeout=90)
        if result.returncode:
            return {"__error__": result.stderr[:200] or f"gh exit {result.returncode}"}
        return json.loads(result.stdout)
    except (OSError, UnicodeError, ValueError, subprocess.TimeoutExpired) as exc:
        return {"__error__": str(exc)}


def checked_pages(endpoint, parse):
    return parse(json.dumps(gh(endpoint, "--paginate", "--slurp")))


def issue_policy_reason(repo, issue):
    labels, assignees = issue.get("labels"), issue.get("assignees")
    if not isinstance(labels, list) or any(
            not isinstance(label, dict) or not isinstance(label.get("name"), str)
            or not label["name"].strip() for label in labels):
        return "labels missing/invalid; recheck required"
    if not isinstance(assignees, list) or any(
            not isinstance(user, dict) or not isinstance(user.get("login"), str)
            or not user["login"].strip() for user in assignees):
        return "assignees missing/invalid; recheck required"
    return policy_reason(repo, [label["name"] for label in labels],
                         [user["login"] for user in assignees])


def scan(days, maxc):
    pool = read_json_object(POOL)
    watch = [item["repo"] for item in pool["watch"]]
    heavy = {item["repo"].lower() for item in pool["watch"] if item.get("heavy") or item.get("rust")}
    blocked = {repo.lower() for repo in pool["blocked"]["repos"]}
    # Old installations use the live account ledger; new clones have the canonical cache.
    if Path(LEDGER).exists():
        inflight = {item["repository"]["nameWithOwner"].lower()
                    for item in read_json_object(LEDGER)["external"]}
    else:
        inflight = {key.split('#')[0].lower() for key, pr in load_pr_state(ROOT / "pr_state.json", ()).items()
                    if pr.get("state") == "OPEN"}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    clean, skipped, unknown = [], [], []
    scanned = 0
    for repo in watch:
        if repo.lower() in heavy:
            skipped.append((repo, "heavy/rust-skip"))
            continue
        if repo.lower() in blocked:
            skipped.append((repo, "blocked"))
            continue
        if repo.lower() in inflight:
            skipped.append((repo, "in-flight"))
            continue
        scanned += 1
        issues = gh(f"repos/{repo}/issues?labels=bug&state=open&sort=created&direction=desc&per_page=8")
        if not isinstance(issues, list):
            unknown.append((repo, "issue list query failed or invalid"))
            continue
        candidates = []
        for issue in issues:
            if not isinstance(issue, dict):
                unknown.append((repo, "invalid issue"))
                continue
            if "pull_request" in issue:
                continue
            reason = issue_policy_reason(repo, issue)
            if reason:
                skipped.append((f"{repo}#{issue.get('number', '?')}", reason))
                continue
            errors = issue_errors(dict(issue, state=str(issue.get("state", "")).upper()))
            if (errors or type(issue.get("number")) is not int or issue["number"] <= 0
                    or not isinstance(issue.get("title"), str)
                    or not isinstance(issue.get("created_at"), str)):
                unknown.append((repo, "incomplete issue; recheck required"))
                continue
            if issue["state"] != "open" or issue["created_at"][:10] < cutoff:
                continue
            body = issue["body"]
            if SOFT.search(body) or NOT_READY.search(body):
                skipped.append((f"{repo}#{issue['number']}", "claimed/not ready"))
                continue
            if FIXED_IN_PR.search(body):
                continue
            candidates.append(issue)
        if not candidates:
            continue
        try:
            pulls = checked_pages(f"repos/{repo}/pulls?state=open&sort=created&direction=desc&per_page=100",
                                  paginated_items)
            if any(not isinstance(pr.get("title"), str) or "body" not in pr
                   or (pr["body"] is not None and not isinstance(pr["body"], str)) for pr in pulls):
                raise ValueError("invalid pull request fields")
            recent_refs = {number for pr in pulls
                           for number in issue_references(f"{pr['title']} {pr['body'] or ''}", repo)}
        except ValueError as exc:
            unknown.append((repo, f"pulls: {exc}"))
            continue
        for issue in candidates[:3]:
            number = issue["number"]
            key = f"{repo}#{number}"
            if number in recent_refs:
                continue
            try:
                if checked_pages(f"repos/{repo}/issues/{number}/timeline?per_page=100", linked_prs):
                    continue
            except ValueError as exc:
                unknown.append((key, f"timeline: {exc}"))
                continue
            try:
                comments = checked_pages(f"repos/{repo}/issues/{number}/comments?per_page=100", comment_bodies)
            except ValueError as exc:
                unknown.append((key, f"comments: {exc}"))
                continue
            if any(SOFT.search(body) or NOT_READY.search(body) for body in comments):
                continue
            clean.append({"repo": repo, "number": number, "title": issue["title"],
                          "created": issue["created_at"][:10], "comments": issue.get("comments", 0),
                          "url": f"https://github.com/{repo}/issues/{number}"})
            if len(clean) >= maxc:
                break
        time.sleep(2)
        if len(clean) >= maxc:
            break

    atomic_write_json(OUT, {"scanned_at": datetime.now(timezone.utc).isoformat(), "days": days,
                            "scanned_repos": scanned, "skipped": skipped,
                            "unknown": unknown, "candidates": clean})
    print(f"scanned {scanned} repos; clean candidates={len(clean)}; unknown={len(unknown)}")
    for candidate in clean:
        print(f"  CLEAN {candidate['repo']}#{candidate['number']} {candidate['title'][:60]}")
    for key, reason in unknown:
        print(f"  UNKNOWN {key}: {reason}")
    print(f"-> {OUT}")
    return 1 if unknown else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=2)
    parser.add_argument("--max", type=int, default=6, dest="maxc")
    args = parser.parse_args(argv)
    if args.days < 0 or args.maxc < 1:
        parser.error("--days must be non-negative and --max must be positive")
    with file_lock(OUT):
        return scan(args.days, args.maxc)


if __name__ == "__main__":
    sys.exit(main())
