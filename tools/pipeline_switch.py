"""One command to start or stop both lanes.

Lane 1 (discovery) runs in Actions: a long shift polls the watched pool every
fifteen minutes and appends new issues to the inbox. Lane 2 (execution) is the
hourly pipeline that reads that inbox and does the actual work. Both consult the
same switch, so a single command stops discovery *and* keeps the hourly run from
starting new work -- stopping one lane while the other keeps going is how you
end up with a full inbox and nothing consuming it.

State lives in the repository variable PIPELINE_ENABLED, because that is the
copy Actions can read without a redeploy. A local mirror is written too, for the
execution side to check before it starts, since the desktop pipeline does not
have the token handy at that moment.

    python tools/pipeline_switch.py status
    python tools/pipeline_switch.py off            # and cancel the running shift
    python tools/pipeline_switch.py off --keep-running
    python tools/pipeline_switch.py on

Unset means on. Only an explicit `false` stops anything, so the lane keeps
working for anyone who never touched the switch.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = "inchang-ing/zcode-PR"
VARIABLE = "PIPELINE_ENABLED"
WORKFLOW = "fresh-issue-poll.yml"
FLAG = Path(__file__).resolve().parents[1] / "work" / "pipeline.enabled"


def gh_bin() -> str:
    found = shutil.which("gh")
    if found:
        return found
    windows = Path(r"C:\Program Files\GitHub CLI\gh.exe")
    if windows.exists():
        return str(windows)
    sys.exit("gh CLI not found on PATH")


def gh(*args: str) -> tuple[int, str, str]:
    proc = subprocess.run([gh_bin(), *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def remote_state() -> str | None:
    """The variable's value, or None when it was never set."""
    code, out, _ = gh("variable", "get", VARIABLE, "--repo", REPO)
    return out if code == 0 and out else None


def local_state() -> str | None:
    if not FLAG.exists():
        return None
    return FLAG.read_text(encoding="utf-8").strip() or None


def is_on(value: str | None) -> bool:
    return (value or "").strip().lower() != "false"


def running_shifts() -> list[str]:
    code, out, _ = gh(
        "run", "list", "--repo", REPO, "--workflow", WORKFLOW,
        "--limit", "10", "--json", "databaseId,status",
    )
    if code != 0 or not out:
        return []
    try:
        runs = json.loads(out)
    except json.JSONDecodeError:
        return []
    return [str(r["databaseId"]) for r in runs if r.get("status") in ("in_progress", "queued")]


def set_switch(on: bool, cancel: bool) -> int:
    value = "true" if on else "false"
    code, _, err = gh("variable", "set", VARIABLE, "--repo", REPO, "--body", value)
    if code != 0:
        print(f"could not set {VARIABLE}: {err}")
        return 1
    FLAG.parent.mkdir(parents=True, exist_ok=True)
    FLAG.write_text("on" if on else "off", encoding="utf-8")
    print(f"{VARIABLE} = {value}  (local mirror: {FLAG})")

    if on:
        print("discovery resumes on the next cron hit; the hourly pipeline may start work again")
        return 0

    ids = running_shifts()
    if not ids:
        print("no shift is running, nothing to cancel")
        return 0
    if not cancel:
        print(f"shift(s) {', '.join(ids)} still running; they stop within one interval")
        return 0
    for run_id in ids:
        code, _, err = gh("run", "cancel", run_id, "--repo", REPO)
        print(f"cancel {run_id}: {'ok' if code == 0 else err}")
    return 0


def status() -> int:
    remote = remote_state()
    local = local_state()
    print(f"variable {VARIABLE}: {remote if remote is not None else '(unset -> on)'}")
    print(f"local mirror       : {local if local is not None else '(unset -> on)'}")
    print(f"effective          : {'ON' if is_on(remote) and is_on(local) else 'OFF'}")
    ids = running_shifts()
    print(f"shifts running     : {', '.join(ids) if ids else 'none'}")
    if ids:
        code, out, _ = gh("run", "view", ids[0], "--repo", REPO,
                          "--json", "createdAt,url", "--jq", ".createdAt + \"  \" + .url")
        if code == 0 and out:
            print(f"latest shift       : {out}")
    return 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    action = args[0] if args else "status"
    if action == "on":
        return set_switch(True, cancel=False)
    if action == "off":
        return set_switch(False, cancel="--keep-running" not in sys.argv)
    if action == "status":
        return status()
    print(__doc__.strip().splitlines()[-1])
    print(f"unknown action: {action}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
