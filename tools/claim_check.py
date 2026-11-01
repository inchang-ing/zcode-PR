"""Check whether an issue has already been claimed in its comments.

Timeline cross-references only show PRs. Someone who says "I'd like to take
this" and is still waiting for assignment produces no cross-reference at all,
so a clean timeline is NOT evidence that an issue is free.

Usage: python tools/claim_check.py owner/repo#123 [owner/repo#456 ...]
Exit code 1 if any issue is already claimed.
"""
import json
import re
import subprocess
import sys

GH = r"C:\Program Files\GitHub CLI\gh.exe"

CLAIM_PATTERNS = [
    r"i(?:'d| would) like to (?:take|work on|pick)",
    r"i(?:'ll| will) (?:take|work on|do) (?:this|it)",
    r"i can (?:take|do|work on)",
    r"can i (?:take|work on)",
    r"\bclaim(?:ing|ed)?\b",
    r"please assign",
    r"assign (?:this|it|me)",
    r"waiting for (?:the )?assign",
    r"(?:fix|patch|branch) (?:is )?ready",
    r"i have a (?:fix|patch|pr)",
    r"working on (?:this|it)",
]


def parse(ref):
    m = re.match(r"([^#]+)#(\d+)$", ref.strip())
    if not m:
        raise SystemExit(f"bad ref: {ref} (expected owner/repo#N)")
    return m.group(1), int(m.group(2))


def comments(repo, n):
    r = subprocess.run(
        [GH, "api", f"repos/{repo}/issues/{n}/comments?per_page=100",
         "--jq", '[.[]|{u:.user.login,t:.created_at,b:.body}]'],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    if r.returncode != 0:
        return None, (r.stderr or "")[:120]
    return json.loads(r.stdout), None


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
            if "bot" in c["u"].lower():
                continue
            low = c["b"].lower()
            for p in CLAIM_PATTERNS:
                if re.search(p, low):
                    hits.append((c["u"], c["t"][:16], p))
                    break
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
