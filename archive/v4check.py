#!/usr/bin/env python
"""v4 collision check for candidate issues.

For each repo#n: confirm OPEN, list cross-referenced PRs (with state), scan
comments for soft-claim phrases, and search open PRs by keyword.
Usage: python v4check.py owner/repo#num [owner/repo#num ...] [--kw "words"]
"""
import json
import re
import subprocess
import sys

CLAIM = re.compile(
    r"(i('d| would) like to (work|take)|taking (a look at )?this|"
    r"working on (a )?(fix|this|pr)|can (i|you) assign|assign (this|it) to me|"
    r"i('m| am) (currently )?working|opened a pr|raised a pr|pr is (ready|up)|"
    r"already (fixed|have a fix)|i have (a|submitted)|happy to prepare)",
    re.I,
)


def gh(args):
    return subprocess.run(["gh"] + args, capture_output=True, text=True, encoding="utf-8")


def check(spec, kw=None):
    repo, num = spec.split("#")
    owner, name = repo.split("/")
    print(f"=== {repo}#{num}")
    q = """
    query($owner:String!,$name:String!,$n:Int!){
      repository(owner:$owner,name:$name){
        issue(number:$n){
          state stateReason title createdAt
          labels(first:6){nodes{name}}
          comments(first:10){nodes{author{login} body}}
        }
      }
    }"""
    p = gh(["api", "graphql", "-f", f"query={q}", "-F", f"owner={owner}",
            "-F", f"name={name}", "-F", f"n={num}"])
    try:
        issue = json.loads(p.stdout)["data"]["repository"]["issue"]
    except Exception as e:
        print(f"  ERROR {p.stdout[:200]} {p.stderr[:200]}")
        return
    print(f"  state={issue['state']}/{issue['stateReason']} "
          f"labels={[l['name'] for l in issue['labels']['nodes']]}")
    print(f"  title: {issue['title'][:120]}")
    # REST timeline, fully paginated: GraphQL timelineItems(first:N) is ordered
    # oldest-first, so a truncated page silently misses the newest
    # cross-references (the ones that matter).
    t = gh(["api", f"repos/{repo}/issues/{num}/timeline", "--paginate"])
    try:
        tl_all = json.loads(t.stdout)
    except Exception:
        print(f"  ERROR timeline: {t.stdout[:150]} {t.stderr[:150]}")
        tl_all = []
    refs = []
    for ev in tl_all:
        if ev.get("event") != "cross-referenced":
            continue
        src = ev.get("source") or {}
        issue_ref = src.get("issue") or {}
        if not issue_ref.get("pull_request"):
            continue  # cross-referenced issue, not a PR
        pr_num = issue_ref["number"]
        d = gh(["api", f"repos/{repo}/pulls/{pr_num}", "--jq",
                "{number,state,merged,title,draft}"])
        try:
            payload = json.loads(d.stdout)
        except Exception:
            continue
        refs.append({
            "number": payload.get("number", pr_num),
            "state": "OPEN" if payload.get("state") == "open" and not payload.get("merged")
                     else ("MERGED" if payload.get("merged") else "CLOSED"),
            "isDraft": payload.get("draft"),
            "title": payload.get("title", ""),
        })
    for r in refs:
        flag = "BLOCKER" if (r["state"] == "OPEN" and not r["isDraft"]) else r["state"]
        print(f"  xref #{r['number']} [{flag}] {r['title'][:80]}")
    if not refs:
        print("  xref: none")
    for c in issue["comments"]["nodes"]:
        body = (c["body"] or "").replace("\r", "")
        if CLAIM.search(body):
            print(f"  !! CLAIM-ish comment by {c['author']['login']}: "
                  f"{body[:160]}")
    if kw:
        r = gh(["pr", "list", "--repo", repo, "--state", "open",
                "--search", kw, "--limit", "6", "--json", "number,title"])
        try:
            for pr in json.loads(r.stdout):
                print(f"  kw-PR #{pr['number']} {pr['title'][:80]}")
        except Exception:
            print("  kw-PR: none")


if __name__ == "__main__":
    args = sys.argv[1:]
    kw = None
    if "--kw" in args:
        i = args.index("--kw")
        kw = args[i + 1]
        args = args[:i] + args[i + 2:]
    for a in args:
        check(a, kw)
