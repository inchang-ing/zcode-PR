"""Small read adapter for gh: UTF-8, bounded calls and complete JSON results."""
import json
from pathlib import Path
import shutil
import subprocess


class GitHubReadError(RuntimeError):
    pass


def gh_binary():
    found = shutil.which("gh")
    if found:
        return found
    windows = Path(r"C:\Program Files\GitHub CLI\gh.exe")
    return str(windows) if windows.is_file() else "gh"


def output(args, *, timeout=60):
    try:
        result = subprocess.run([gh_binary(), *args], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitHubReadError(f"GitHub CLI unavailable or request failed: {exc}") from exc
    if result.returncode:
        raise GitHubReadError(result.stderr.strip()[:300] or "GitHub query failed")
    return result.stdout.strip()


def paginated_items(raw, *, item_key=None, search=False):
    try:
        pages = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise GitHubReadError("Invalid JSON response") from exc
    if not isinstance(pages, list) or not pages:
        raise GitHubReadError("Missing paginated response")
    items = []
    for page in pages:
        if search and (not isinstance(page, dict) or page.get("incomplete_results") is not False
                       or type(page.get("total_count")) is not int
                       or not 0 <= page["total_count"] <= 1000):
            raise GitHubReadError("Search results are incomplete")
        rows = (page.get(item_key) if isinstance(page, dict) else None) if item_key is not None else page
        if not isinstance(rows, list) or any(not isinstance(item, dict) for item in rows):
            raise GitHubReadError("Invalid page response")
        items.extend(rows)
    if search and any(len(items) < page["total_count"] for page in pages):
        raise GitHubReadError("Search returned fewer results than expected")
    return items


def api(path, accept="application/vnd.github+json", *, paginate=False, item_key=None, search=False):
    args = ["api", "-H", f"Accept: {accept}"]
    if paginate:
        args += ["--paginate", "--slurp"]
    args.append(path)
    raw = output(args)
    if paginate:
        return paginated_items(raw, item_key=item_key, search=search)
    try:
        result = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise GitHubReadError("Invalid JSON response") from exc
    if not isinstance(result, dict):
        raise GitHubReadError("Expected an object response")
    return result
