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

A successfully queried unset value means on. Query failures and malformed
state are errors, never an implicit enable. New writes use true/false; legacy
on/off values remain readable. Default off also cancels active shifts. With
--keep-running, a shift lacking Variables API access may finish using its
start-of-job value.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from pipeline_state import atomic_write_text, file_lock

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
    proc = subprocess.run([gh_bin(), *args], capture_output=True, text=True, timeout=30)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def remote_state() -> str | None:
    """The variable's value, or None when it was never set."""
    code, out, err = gh('variable', 'list', '--repo', REPO, '--json', 'name,value')
    if code != 0:
        raise RuntimeError('switch query failed: ' + err[:300])
    variables = json.loads(out)
    if not isinstance(variables, list):
        raise ValueError('Invalid switch response')
    return next((item['value'] for item in variables if item['name'] == VARIABLE), None)


def local_state() -> str | None:
    if not FLAG.exists():
        return None
    value = FLAG.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError('Local switch file is empty; refusing to enable')
    return value


def is_on(value: str | None) -> bool:
    value = (value or '').strip().lower()
    if value not in {'', 'on', 'off', 'true', 'false'}:
        raise ValueError('Invalid pipeline switch value')
    return value not in {'off', 'false'}


def running_shifts() -> list[str]:
    code, out, _ = gh(
        "run", "list", "--repo", REPO, "--workflow", WORKFLOW,
        "--limit", "10", "--json", "databaseId,status",
    )
    if code != 0:
        raise RuntimeError('Could not list shifts; cancellation is unverified')
    runs = json.loads(out)
    return [str(r["databaseId"]) for r in runs if r.get("status") in ("in_progress", "queued")]


def set_switch(on: bool, cancel: bool) -> int:
    value = "true" if on else "false"
    code, _, err = gh("variable", "set", VARIABLE, "--repo", REPO, "--body", value)
    if code != 0:
        print(f"could not set {VARIABLE}: {err}")
        return 1
    try:
        with file_lock(FLAG):
            atomic_write_text(FLAG, value + '\n')
    except (OSError, RuntimeError) as exc:
        raise RuntimeError('远端开关已保存，本地镜像未刷新；请重试同一开关命令') from exc
    print(f"{VARIABLE} = {value}  (local mirror: {FLAG})")

    if on:
        print("discovery resumes on the next cron hit; the hourly pipeline may start work again")
        return 0

    ids = running_shifts()
    if not ids:
        print("no shift is running, nothing to cancel")
        return 0
    if not cancel:
        print(f"shift(s) {', '.join(ids)} still running; without Variables API access they may finish this shift")
        return 0
    failed = False
    for run_id in ids:
        code, _, err = gh("run", "cancel", run_id, "--repo", REPO)
        print(f"cancel {run_id}: {'ok' if code == 0 else err}")
        failed |= code != 0
    return int(failed)


def status() -> int:
    try:
        remote = remote_state()
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        local = local_state()
        print(f'variable {VARIABLE}: UNKNOWN ({exc})')
        print(f'local mirror       : {local}')
        print('effective          : ' + ('OFF' if local is not None and not is_on(local) else 'UNKNOWN'))
        return 1
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
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        sys.exit(f'ERROR: {exc}')
