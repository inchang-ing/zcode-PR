#!/usr/bin/env python
"""Find open issues that are free to work on: no open cross-referenced PR and
no soft-claim language in the body or comments.

One GraphQL page per repo.
Usage: python scan_clean.py owner/repo [owner/repo ...]
"""
import json
import re
import subprocess
import sys

CLAIM = re.compile(
    r"(i('d| would) like to (work on|take|fix|pick)|taking (a look at )?this|"
    r"working on (a )?(fix|this|a pr)|can (i|you) assign|assign (this|it) to me|"
    r"i('m| am) (currently )?(working|preparing)|opened a pr|raised a pr|"
    r"pr is (ready|up|on the way)|already (fixed|have a fix)|i have (a|submitted)|"
    r"happy to (prepare|open a pr|submit|take)|i can (open|submit) a pr|"
    r"would like to (submit|contribute)|i will (open|submit)|"
    r"interest(ed)? in (working|taking)|planning to (pick|work)|"
    r"let me (take|work)|i've (opened|submitted)|if you'd like i can)",
    re.I,
)

Q = """
query($owner: String!, $name: String!, $n: Int!) {
  repository(owner: $owner, name: $name) {
    issues(first: $n, states: OPEN, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        number title createdAt body
        comments(first: 8) { totalCount nodes { author { login } body } }
        labels(first: 5) { nodes { name } }
        timelineItems(first: 20, itemTypes: [CROSS_REFERENCED_EVENT]) {
          nodes { ... on CrossReferencedEvent { source { __typename
                  ... on PullRequest { number state isDraft } } } }
        }
      }
    }
  }
}
"""

BODY_Q = """
query($owner: String!, $name: String!, $n: Int!) {
  repository(owner: $owner, name: $name) { issue(number: $n) { body } }
}
"""


def gql(q, **vars_):
    args = ["gh", "api", "graphql", "-f", f"query={q}"]
    for k, v in vars_.items():
        args += ["-F", f"{k}={v}"]
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8")


def run(repo, n=60):
    owner, name = repo.split("/")
    p = gql(Q, owner=owner, name=name, n=n)
    try:
        data = json.loads(p.stdout)
        nodes = data["data"]["repository"]["issues"]["nodes"]
    except Exception:
        print(f"=== {repo}: ERROR {p.stdout[:150]} {p.stderr[:150]}")
        return
    out = []
    for it in nodes:
        refs = [tl["source"] for tl in it["timelineItems"]["nodes"]
                if (tl.get("source") or {}).get("__typename") == "PullRequest"]
        if [r for r in refs if r["state"] == "OPEN" and not r["isDraft"]]:
            continue  # colliding open PR
        hits = []
        body = it.get("body") or ""
        if CLAIM.search(body):
            hits.append("body")
        for c in it["comments"]["nodes"]:
            if CLAIM.search(c["body"] or ""):
                hits.append(c["author"]["login"])
        if hits:
            continue  # soft-claimed
        labs = ",".join(l["name"] for l in it["labels"]["nodes"])
        closed = ",".join(f"#{r['number']}:{r['state']}" for r in refs)
        out.append((it, labs, closed))
    print(f"=== {repo}  ({len(out)} free / {len(nodes)} scanned)")
    for it, labs, closed in out:
        print(f"  #{it['number']} [{it['createdAt'][:10]}] c={it['comments']['totalCount']} "
              f"[{labs}] refs={closed or '-'} {it['title'][:120]}")


if __name__ == "__main__":
    for r in sys.argv[1:] or ["optuna/optuna"]:
        run(r)
