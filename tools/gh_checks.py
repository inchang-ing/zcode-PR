"""Validate GitHub responses before treating a candidate as checked."""
import json


def issue_errors(issue):
    if not isinstance(issue, dict):
        return ["issue 不是对象"]
    errors = []
    if issue.get("state") not in ("OPEN", "CLOSED"):
        errors.append("state 缺失或无效")
    if not isinstance(issue.get("assignees"), list):
        errors.append("assignees 缺失或无效")
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
    if output is None:
        raise ValueError("请求失败或超时")
    try:
        pages = json.loads(output)
    except (ValueError, TypeError) as exc:
        raise ValueError("返回无效 JSON") from exc
    if not isinstance(pages, list) or not pages or any(
        not isinstance(page, list) for page in pages
    ):
        raise ValueError("分页返回结构无效")
    items = [item for page in pages for item in page]
    if any(not isinstance(item, dict) for item in items):
        raise ValueError("分页记录不是对象")
    return items


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
            # REST puts the PR number on source.issue, not on pull_request.
            prs.append(issue.get("number") or issue.get("html_url") or "未知编号")
    return prs


def comment_bodies(output):
    comments = paginated_items(output)
    if any(not isinstance(comment.get("body"), str) for comment in comments):
        raise ValueError("评论 body 缺失或无效")
    return [comment["body"] for comment in comments]
