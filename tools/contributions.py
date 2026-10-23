"""Evidence-backed contribution records and a generated Markdown ledger (stdlib only)."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, quote

from pipeline_state import atomic_write_json, atomic_write_text, file_lock
from pr_state import load_pr_state, utc_now

ROOT = Path(__file__).resolve().parents[1]
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value):
    require(isinstance(value, str), "核验时间必须是带时区的 ISO 时间")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("无效的 ISO 时间") from None
    require(parsed.tzinfo is not None, "核验时间必须包含时区")


def record_id(repo, issue):
    require(isinstance(repo, str) and REPO.fullmatch(repo), "无效仓库名")
    require(all(part not in {'.', '..'} for part in repo.split('/')), "无效仓库名")
    require(type(issue) is int and issue > 0, "issue 必须是正整数")
    return f"{repo.lower().replace('/', '--')}--issue-{issue}"


def new_record(repo, issue, title, pr=None, problem_type="unknown", approach="unknown"):
    return {
        "schema_version": 1, "id": record_id(repo, issue), "repo": repo,
        "issue": issue, "pr": pr, "title": title, "problem_type": problem_type,
        "approach": approach, "created_at": utc_now(),
        "policy": {"status": "unverified", "checked_at": None, "summary": "", "sources": []},
        "collision": {"status": "unverified", "checked_at": None, "summary": "", "sources": []},
        "verification": {"status": "unverified", "case": "", "summary": "",
                         "before": None, "after": None},
        "feedback": {"checked_at": None, "items": []},
        "outcome": {"reason_category": "unknown", "summary": "", "sources": []},
        "next_actions": [], "provenance": [],
    }


def validate_sources(sources, root):
    require(isinstance(sources, list), "sources 必须是列表")
    for source in sources:
        require(isinstance(source, dict), "证据必须是对象")
        ref = source.get("ref")
        require(isinstance(ref, str) and ref, "证据缺少 ref")
        if source.get("kind") == "url":
            url = urlsplit(ref)
            require(url.scheme == "https" and url.hostname and not url.username
                    and not any(c.isspace() for c in ref), "证据链接必须是有效 HTTPS URL")
        else:
            require(source.get("kind") == "local", "未知证据类型")
            require(ref.startswith("contributions/evidence/"), "证据路径必须是仓库相对路径")
            path = (root / ref).resolve()
            evidence = (root / "contributions/evidence").resolve()
            require(evidence.is_relative_to(root.resolve()) and path.is_relative_to(evidence),
                    "本地证据必须位于 contributions/evidence 内")
            require(path.is_file(), f"缺少证据文件: {ref}")
            require(hashlib.sha256(path.read_bytes()).hexdigest() == source.get("sha256"),
                    f"证据摘要不匹配: {ref}")


def validate(record, root=ROOT):
    require(isinstance(record, dict), "贡献记录必须是对象")
    require(type(record.get("schema_version")) is int and record['schema_version'] == 1, "不支持的记录版本")
    require(record.get("id") == record_id(record.get("repo"), record.get("issue")), "记录 ID 不匹配")
    require(record.get("pr") is None or (type(record["pr"]) is int and record["pr"] > 0), "无效 PR 编号")
    for key in ("title", "problem_type", "approach"):
        require(isinstance(record.get(key), str) and record[key].strip(), f"缺少 {key}")
    timestamp(record.get("created_at"))
    validate_sources(record.get("provenance"), root)
    required_sections = {
        'policy': {'status', 'checked_at', 'summary', 'sources'},
        'collision': {'status', 'checked_at', 'summary', 'sources'},
        'verification': {'status', 'case', 'summary', 'before', 'after'},
        'feedback': {'checked_at', 'items'},
        'outcome': {'reason_category', 'summary', 'sources'},
    }
    for name, keys in required_sections.items():
        require(isinstance(record.get(name), dict) and keys <= record[name].keys(), f'{name} 缺少必需字段')
    for key in ("policy", "collision"):
        section = record.get(key)
        require(isinstance(section, dict), f"缺少 {key}")
        require(section.get("status") in {"unverified", "verified"}, f"无效 {key} 状态")
        require(isinstance(section.get("summary"), str), f"缺少 {key} 摘要")
        validate_sources(section.get("sources"), root)
        if section.get("checked_at") is not None:
            timestamp(section["checked_at"])
        if section["status"] == "verified":
            timestamp(section.get("checked_at"))
            require(section["sources"] and section["summary"].strip(), f"{key} 不能无证据核验")
    verification = record.get("verification")
    require(isinstance(verification, dict), "缺少 verification")
    require(verification.get("status") in {"unverified", "recorded"}, "无效测试证据状态")
    for key in ("case", "summary"):
        require(isinstance(verification.get(key), str), f"缺少 verification.{key}")
    for phase in ("before", "after"):
        run = verification.get(phase)
        if run is None:
            require(verification["status"] == "unverified", "完整验证必须同时包含修复前后运行")
            continue
        require(isinstance(run, dict), "测试运行必须是对象")
        require(isinstance(run.get("commit"), str) and re.fullmatch(r"[0-9a-f]{40}", run['commit']),
                "测试须记录完整提交 SHA")
        for key in ("command", "environment", "test_case"):
            require(isinstance(run.get(key), str) and run[key].strip(), f"测试缺少 {key}")
        timestamp(run.get("ran_at"))
        require(type(run.get("exit_code")) is int, "测试缺少退出码")
        require(run.get("result") in {"regression_failed", "passed", "environment_error"}, "缺少测试结果分类")
        if 'scope' in run:
            require(isinstance(run['scope'], str) and run['scope'] in {'project', 'isolated', 'stub'}, "无效测试范围")
        require(isinstance(run.get("log"), dict) and run["log"].get("kind") == "local", "须保存本地测试日志")
        validate_sources([run["log"]], root)
    if verification["status"] == "recorded":
        before, after = verification["before"], verification["after"]
        require(verification["case"].strip(), "缺少回归测试标识")
        require(before["test_case"] == after["test_case"] == verification["case"], "前后必须验证同一回归用例")
        require(before["environment"] == after["environment"], "前后测试环境不一致")
        require(before["commit"] != after["commit"], "修复前后须记录不同提交")
        require(before["exit_code"] != 0 and before["result"] == "regression_failed",
                "修复前必须为回归失败，环境失败不能作为证据")
        require(after["exit_code"] == 0 and after["result"] == "passed", "修复后必须通过")
    feedback = record.get("feedback")
    require(isinstance(feedback, dict) and isinstance(feedback.get("items"), list), "无效反馈")
    if feedback.get("checked_at") is not None:
        timestamp(feedback["checked_at"])
    for item in feedback["items"]:
        require(isinstance(item, dict) and item.get("kind") in {"fact", "interpretation"}, "反馈须区分事实与判断")
        require(isinstance(item.get("summary"), str) and item["summary"].strip(), "反馈缺少摘要")
        timestamp(item.get("observed_at"))
        validate_sources(item.get("sources"), root)
        require(item["sources"], "反馈须有来源，推测也应引用依据")
        if item["kind"] == "fact":
            require(any(s["kind"] == "url" for s in item["sources"]), "维护者反馈事实须附原始评论或评审链接")
    outcome = record.get("outcome")
    require(isinstance(outcome, dict) and outcome.get("reason_category") in
            {"unknown", "duplicate", "scope", "tests", "other"}, "无效结果原因分类")
    require(isinstance(outcome.get("summary"), str), "缺少结果摘要")
    validate_sources(outcome.get("sources"), root)
    if outcome["reason_category"] != "unknown":
        require(outcome["summary"].strip() and any(s["kind"] == "url" for s in outcome["sources"]),
                "归因须有原始反馈链接，不能凭关闭状态猜测")
    require(isinstance(record.get("next_actions"), list) and
            all(isinstance(s, str) and s.strip() for s in record["next_actions"]), "无效待办")


def load_records(root=ROOT):
    records, prs = [], set()
    for path in sorted((root / "contributions/records").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8-sig"))
        validate(record, root)
        require(path.stem == record["id"], f"文件名与 ID 不一致: {path.name}")
        if record["pr"] is not None:
            key = (record["repo"].lower(), record["pr"])
            require(key not in prs, f"重复 PR: {key}")
            prs.add(key)
        records.append(record)
    return records


def cell(value):
    return html.escape(str(value), quote=False).replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def source_links(sources):
    return "、".join(f"[来源{i}]({quote(s['ref'], safe='/:#?=&%')})" for i, s in enumerate(sources, 1)) or "无"


def render(records, cache):
    states = {}
    cache = {k.lower(): v for k, v in cache.items()}
    for record in records:
        key = f"{record['repo']}#{record['pr']}".lower()
        observation = cache.get(key, {})
        states[record["id"]] = observation
    lines = ["# 贡献记录", "", f"生成时间：{utc_now()}", "",
             "由 contributions/records/*.json 生成，请勿手改。仅覆盖已导入样本，不代表全部贡献。",
             "PR 状态只读取 pr_state.json 缓存，展示最后核验时间；未联网更新。",
             "生成器只校验测试证据字段和日志摘要；是否补做、何时执行，以任务说明和运行时间为准，不自动审核日志语义。", "",
             "| 贡献 | 问题类型 / 修复方式 | 缓存状态 / 核验时间 | 政策 / 撞车 | 测试证据 |",
             "| --- | --- | --- | --- | --- |"]
    for r in records:
        obs = states[r["id"]]
        state = (obs.get("state") or "未核验") + ("（查询失败，保留旧值）" if obs.get("query_error") else "")
        lines.append(f"| [{cell(r['id'])}](#{r['id']}) | {cell(r['problem_type'])} / {cell(r['approach'])} | "
                     f"{cell(state)} / {cell(obs.get('checked_at', '未记录'))} | "
                     f"{r['policy']['status']} / {r['collision']['status']} | {r['verification']['status']} |")
    lines += ["", "## 样本统计", "", "unknown 表示尚未核验；未结束的 PR 不计入已结束样本分母。",
              "本表按缓存统计，不据此自动推荐仓库；小样本不能推断贡献质量。", ""]
    for field, label in (("repo", "仓库"), ("problem_type", "问题类型"), ("approach", "修复方式")):
        lines += ["", f"### 按{label}", "", "| 分组 | 样本 | MERGED | CLOSED | OPEN | 未知/查询失败 | 已结束样本合并比 |",
                  "| --- | --- | --- | --- | --- | --- | --- |"]
        for value in sorted({r[field] for r in records}):
            group = [r for r in records if r[field] == value]
            counts = Counter(states[r['id']].get('state', 'unknown')
                             if states[r['id']].get('state') in {'MERGED', 'CLOSED', 'OPEN'}
                             and states[r['id']].get('checked_at') and not states[r['id']].get('query_error')
                             else 'unknown' for r in group)
            merged, closed = counts['MERGED'], counts['CLOSED']
            ratio = f"{merged}/{merged + closed}" if merged + closed else "不适用"
            lines.append(f"| {cell(value)} | {len(group)} | {merged} | {closed} | {counts['OPEN']} | {counts['unknown']} | {ratio} |")
    lines += ["", "## 任务详情"]
    for r in records:
        lines += ["", f"## {r['id']}", "", cell(r['title']), "",
                  f"[Issue](https://github.com/{r['repo']}/issues/{r['issue']})" +
                  (f" · [PR](https://github.com/{r['repo']}/pull/{r['pr']})" if r['pr'] else " · 尚未关联 PR"),
                  "", f"导入依据：{source_links(r['provenance'])}"]
        for key, name in (("policy", "政策核验"), ("collision", "撞车核验")):
            section = r[key]
            lines += ["", f"**{name}**：{'未核验' if section['status'] == 'unverified' else '有核验记录'}；"
                      f"时间：{cell(section['checked_at'] or '未记录')}。{cell(section['summary'])} "
                      f"{source_links(section['sources'])}"]
        v = r['verification']
        lines += ["", f"**测试**：{'未核验' if v['status'] == 'unverified' else '已记录 fail→pass 证据'}。{cell(v['summary'])}"]
        for phase in ('before', 'after'):
            run = v[phase]
            if run:
                lines += ["", f"- {phase}: commit={cell(run['commit'])}；环境={cell(run['environment'])}；"
                          f"命令={cell(run['command'])}；退出码={run['exit_code']}；结果={run['result']}；"
                          f"时间={cell(run['ran_at'])}；{source_links([run['log']])}"]
        f = r['feedback']
        lines += ["", f"**维护者反馈**：最后核验 {cell(f['checked_at'] or '未记录')}。"]
        if not f['items']:
            lines += ["尚未录入反馈，不等于维护者没有回复。"]
        for item in f['items']:
            lines += [f"- {'事实' if item['kind'] == 'fact' else '判断'}：{cell(item['summary'])} "
                      f"（{cell(item['observed_at'])}）{source_links(item['sources'])}"]
        o = r['outcome']
        lines += ["", f"**结果归因**：{cell(o['reason_category'])}。{cell(o['summary'])} {source_links(o['sources'])}",
                  "", "**建议待办（非维护者指令）**：", ""]
        lines += [f"- {cell(action)}" for action in r['next_actions']] or ["暂无录入。"]
    return "\n".join(lines) + "\n"


def generate(root=ROOT):
    with file_lock(root / "contributions/records"):
        records = load_records(root)
        cache = load_pr_state(root / "pr_state.json", ())
        atomic_write_text(root / "CONTRIBUTIONS.md", render(records, cache))
    return len(records)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("check", help="校验记录和本地证据摘要，不联网")
    sub.add_parser("render", help="生成贡献台账和样本统计")
    new = sub.add_parser("new", help="创建空白记录；不会覆盖已有任务")
    new.add_argument("repo")
    new.add_argument("issue", type=int)
    new.add_argument("title")
    new.add_argument("--pr", type=int)
    new.add_argument("--problem-type", default="unknown")
    new.add_argument("--approach", default="unknown")
    args = parser.parse_args(argv)
    try:
        if args.action == "new":
            r = new_record(args.repo, args.issue, args.title, args.pr, args.problem_type, args.approach)
            validate(r)
            path = ROOT / "contributions/records" / (r['id'] + ".json")
            with file_lock(ROOT / "contributions/records"):
                require(not path.exists(), "记录已存在，拒绝覆盖")
                atomic_write_json(path, r)
            print(path)
        elif args.action == "check":
            print(f"OK: {len(load_records())} records；证据结构有效，不代表重新执行核验")
        else:
            print(f"Generated CONTRIBUTIONS.md: {generate()} records")
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
