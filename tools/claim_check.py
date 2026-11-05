"""Check whether an issue has already been claimed in its comments.

Timeline cross-references only show PRs. Someone who says "I'd like to take
this" and is still waiting for assignment produces no cross-reference at all,
so a clean timeline is NOT evidence that an issue is free.

Usage: python tools/claim_check.py owner/repo#123 [owner/repo#456 ...]
Exit code 1 if any issue is already claimed.
"""
import re
import github_read
import sys

from claim_rules import SOFT, NOT_READY
from gh_checks import paginated_items

def parse(ref):
    m = re.match(r"([^#]+)#(\d+)$", ref.strip())
    if not m:
        raise SystemExit(f"bad ref: {ref} (expected owner/repo#N)")
    return m.group(1), int(m.group(2))


def comments(repo, n):
    try:
        output = github_read.output(
            ["api", f"repos/{repo}/issues/{n}/comments?per_page=100", "--paginate", "--slurp"], timeout=90)
        items = paginated_items(output)
        comments = []
        for item in items:
            user = item.get("user")
            if (not isinstance(user, dict) or not isinstance(user.get("login"), str)
                    or not user["login"].strip() or not isinstance(item.get("body"), str)
                    or not isinstance(item.get("created_at"), str) or not item["created_at"]):
                raise ValueError("comment body, author or timestamp missing/invalid")
            comments.append({"u": user["login"], "t": item["created_at"], "b": item["body"]})
        return comments, None
    except (github_read.GitHubReadError, UnicodeError, ValueError) as exc:
        return None, str(exc)[:120]


def main():
    refs = sys.argv[1:]
    if not refs:
        raise SystemExit(__doc__)
    claimed_any = False
    for ref in refs:
        repo, n = parse(ref)
        cs, err = comments(repo, n)
        if err:
            print(f"{repo}#{n}: UNKNOWN ({err})")
            claimed_any = True
            continue
        hits = []
        for c in cs:
            match = SOFT.search(c["b"]) or NOT_READY.search(c["b"])
            if match:
                hits.append((c["u"], c["t"][:16], match.group(0)))
        if hits:
            claimed_any = True
            who = "; ".join(f"{u}@{t}" for u, t, _ in hits)
            print(f"{repo}#{n}: CLAIMED by {who}")
            for _, _, p in hits[:3]:
                print(f"    matched: {p}")
        else:
            print(f"{repo}#{n}: CLEAR ({len(cs)} comments, none claimed)")
    sys.exit(1 if claimed_any else 0)


if __name__ == "__main__":
    main()
