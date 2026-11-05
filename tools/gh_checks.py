"""Validate GitHub responses before treating a candidate as checked."""
import github_read


def issue_errors(issue):
    if not isinstance(issue, dict):
        return ["issue 不是对象"]
    errors = []
    if issue.get("state") not in ("OPEN", "CLOSED"):
        errors.append("state 缺失或无效")
    if not isinstance(issue.get("assignees"), list):
        errors.append("assignees 缺失或无效")
    elif any(not isinstance(a, dict) or not isinstance(a.get("login"), str)
             or not a["login"] for a in issue["assignees"]):
        errors.append("assignees login 缺失或无效")
    labels = issue.get("labels")
    if not isinstance(labels, list) or any(
        not isinstance(label, dict) or not isinstance(label.get("name"), str)
        for label in labels
    ):
        errors.append("labels 缺失或无效")
    if not isinstance(issue.get("body"), str):
        errors.append("body 缺失或无效")
    return errors


def paginated_items(output):
    """gh api --paginate --slurp returns one array containing every page."""
    try:
        return github_read.paginated_items(output)
    except github_read.GitHubReadError as exc:
        raise ValueError(str(exc)) from exc


def linked_prs(output):
    prs = []
    for event in paginated_items(output):
        if not isinstance(event.get("event"), str):
            raise ValueError("timeline event 缺失或无效")
        source = event.get("source")
        if source is None:
            continue
        if not isinstance(source, dict):
            raise ValueError("timeline source 结构无效")
        if "issue" not in source:
            continue
        issue = source["issue"]
        if not isinstance(issue, dict):
            raise ValueError("timeline source.issue 结构无效")
        if "pull_request" in issue:
            # 我们自己的 repo-monitor 摘要 issue 会回引每个新捕获的 issue;
            # 那是监控产物,不是竞品 PR,不得作为撞车证据(2026-10-31 发现)。
            repo_url = (issue.get("repository_url") or "").lower()
            if "inchang-ing/repo-monitor" in repo_url:
                continue
            # REST puts the PR number on source.issue, not on pull_request.
            prs.append(issue.get("number") or issue.get("html_url") or "未知编号")
    return prs


def comment_bodies(output):
    comments = paginated_items(output)
    if any(not isinstance(comment.get("body"), str) for comment in comments):
        raise ValueError("评论 body 缺失或无效")
    return [comment["body"] for comment in comments]
