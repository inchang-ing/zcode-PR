#!/usr/bin/env python
"""Fresh-issue monitor: incremental diff over ALL pipeline repo pools.

Fired every ~15 min by the cron automation. Prints only issues CREATED
since the previous check (state in tools/monitor_state.json).

Tiering (rate-limit aware):
  T1  repository_pools.CORE (agent core, ~51)        — every fire
  T2  repository_pools.WATCH + G (~47)   — every fire
  T3  secondary + pools A/B/C/D/E (~340)       — 1/3 rotating slice per
      fire (full coverage ~every 45 min); slice index persists in state.

Usage:
  python monitor_fresh.py            # diff since last check
  python monitor_fresh.py --init     # (re)baseline without reporting
Output:
  NEW: <repo>#<num>  <age>h  <title>  [labels]  (author)
  TEXTUAL-RETRY: yes|no
"""
import json
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline_state import atomic_write_json, file_lock, read_json_object
from candidate_rules import contribution_kind

GH = r"C:\Program Files\GitHub CLI\gh.exe"
STATE_PATH = str(Path(__file__).resolve().parent / "monitor_state.json")
PER_PAGE = 15
PRUNE_DAYS = 7
T3_SLICES = 3
ALWAYS_SLICES = 2  # rotate the always tier across fires (halves per-fire cost)
NOISE_SUBSTRINGS = ("ScreenContextAgent",)

# Compatibility exports for callers; the pool loader contains no scanner code.
from repository_pools import build_tiers, normalize_repo as _norm, load_pool
EXTENSION_POOL = load_pool("EXTENSION_POOL", normalize=False)


def gh_api(path: str) -> str:
    cmd = [GH, "api", path]
    for attempt in (1, 2, 3):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               errors="replace", timeout=90)
            if r.returncode == 0:
                return r.stdout
        except (OSError, subprocess.TimeoutExpired):
            pass
        if attempt < 3:
            import time

            time.sleep(10)  # transient proxy flake (dial tcp 198.18.0.x)
    return ""


def load_state() -> dict:
    return read_json_object(STATE_PATH)


def save_state(state: dict) -> None:
    atomic_write_json(STATE_PATH, state)


def fetch_newest(repo: str, last_check: datetime) -> list[dict] | None:
    """Return all issues since this repo's watermark, or None on any page failure."""
    fresh = []
    page = 1
    while True:
        raw = gh_api(
            f"repos/{repo}/issues?state=all&sort=created&direction=desc"
            f"&per_page={PER_PAGE}&page={page}"
        )
        if not raw:
            return None
        try:
            items = json.loads(raw)
            if not isinstance(items, list):
                return None
            reached_watermark = False
            for it in items:
                created = datetime.fromisoformat(it["created_at"].replace("Z", "+00:00"))
                # Include the boundary second; GitHub creation times have second precision.
                if created < last_check:
                    reached_watermark = True
                    continue
                if "pull_request" in it:
                    continue
                number = it.get("number")
                if type(number) is not int or number <= 0:
                    return None
                title = it.get("title", "")
                if any(n in title for n in NOISE_SUBSTRINGS):
                    continue
                fresh.append({
                    "repo": repo,
                    "num": number,
                    "age_h": round((datetime.now(timezone.utc) - created).total_seconds() / 3600, 2),
                    "title": title,
                    "labels": ",".join(l["name"] for l in it.get("labels", [])),
                    "author": it.get("user", {}).get("login", "?"),
                })
        except (ValueError, KeyError, TypeError, AttributeError):
            return None
        if reached_watermark or len(items) < PER_PAGE:
            return fresh
        page += 1


def persist_discoveries(items):
    path = Path(STATE_PATH).with_name("fresh_candidates.json")
    with file_lock(path):
        inbox = read_json_object(path)
        for item in items:
            key = f"{item['repo'].lower()}#{item['num']}"
            inbox.setdefault(key, {"repo": item['repo'], "number": item['num'],
                "title": item['title'], "url": f"https://github.com/{item['repo']}/issues/{item['num']}",
                "kind": contribution_kind(item['labels'].split(',')),
                "labels": item['labels'].split(',') if item['labels'] else [],
                "issue_unknown": True, "pr_unknown": True, "cmt_unknown": True,
                "check_errors": ["新发现，尚未执行共享核验"]})
        atomic_write_json(path, inbox)


def run_round() -> int:
    init = "--init" in sys.argv
    state = load_state()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if "default_since" not in state:
        # The legacy global watermark skipped rotating/failed repos; replay a safe window.
        last_raw = state.get("last_check")
        start = (datetime.fromisoformat(last_raw) - timedelta(days=PRUNE_DAYS)
                 if last_raw else now - timedelta(minutes=20))
        state["default_since"] = start.isoformat()
    watermarks = state.setdefault("repo_last_success", {})
    seen: dict = state.get("seen", {})

    always, rotating = build_tiers()
    rot_index = int(state.get("rot_index", 0)) % T3_SLICES
    rot_slice = rotating[rot_index::T3_SLICES]
    # The always tier also rotates (default halves): the full ~96-repo always
    # tier is what pushes a fresh fire to ~390 calls, leaving no triage budget.
    alw_index = int(state.get("always_rot_index", 0)) % ALWAYS_SLICES
    always_slice = always[alw_index::ALWAYS_SLICES]
    repos = always_slice + rot_slice

    # --all/--full: scan every repo this fire instead of a rotating slice.
    # Rotation exists for the 45-minute cadence, where 3 slices kept a single
    # repo's discovery latency at ~3h. On an hourly cadence that latency means
    # a good-first-issue is often gone before we ever see it, and the full pool
    # costs ~440 calls/fire against a 5000/hour ceiling — affordable.
    full_scan = "--all" in sys.argv or "--full" in sys.argv
    if full_scan:
        repos = always + rotating

    with ThreadPoolExecutor(max_workers=14) as pool:
        results = list(pool.map(lambda r: fetch_newest(
            r, datetime.fromisoformat(watermarks.get(r, state["default_since"]))), repos))
    status = int(any(items is None for items in results))

    new_items = []
    for repo, items in zip(repos, results):
        if items is None:
            print(f"ERROR: {repo} query incomplete; watermark unchanged")
            continue
        watermarks[repo] = now.isoformat()
        for it in items:
            key = f"{it['repo']}#{it['num']}"
            if key in seen:
                continue
            new_items.append(it)

    if init:
        for items in results:
            for it in items or []:
                seen[f"{it['repo']}#{it['num']}"] = now.isoformat()
        state.update(last_check=now.isoformat(), seen=seen, rot_index=rot_index)
        save_state(state)
        print(
            f"INIT: baselined {len(seen)} seen keys; "
            f"tiers: always={len(always)} (slice {alw_index}/{ALWAYS_SLICES}="
            f"{len(always_slice)} this fire) rotating={len(rotating)} "
            f"(slice {rot_index}/{T3_SLICES}={len(rot_slice)} this fire)"
        )
        return status

    # Persist before advancing seen/watermarks: a failed write can be safely replayed.
    persist_discoveries(new_items)
    cutoff = (now - timedelta(days=PRUNE_DAYS)).isoformat()
    seen = {k: v for k, v in seen.items() if v > cutoff}

    for it in sorted(new_items, key=lambda x: (x["repo"], x["num"])):
        key = f"{it['repo']}#{it['num']}"
        seen[key] = now.isoformat()
        flags = f" [{it['labels']}]" if it["labels"] else ""
        print(
            f"NEW: {it['repo']}#{it['num']}  {it['age_h']}h  {it['title']}"
            f"{flags}  ({it['author']})"
        )
    if not new_items:
        print("NEW: none")

    textual_last = state.get("textual_last")
    retry = (
        "yes"
        if not textual_last
        or now - datetime.fromisoformat(textual_last) > timedelta(minutes=55)
        else "no"
    )
    if retry == "yes":
        state["textual_last"] = now.isoformat()
    state["last_check"] = now.isoformat()
    state["seen"] = seen
    if not full_scan:
        state["rot_index"] = (rot_index + 1) % T3_SLICES
        state["always_rot_index"] = (alw_index + 1) % ALWAYS_SLICES
    save_state(state)
    if full_scan:
        print(f"SCOPE: full scan, {len(repos)} repos (rotation paused)")
    print(f"TEXTUAL-RETRY: {retry}")
    return status


def main() -> int:
    with file_lock(STATE_PATH):
        status = run_round()
    from work_queue import refresh
    refresh()
    return status


if __name__ == "__main__":
    sys.exit(main())
