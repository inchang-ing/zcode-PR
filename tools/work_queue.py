"""Local, explainable contribution scheduling. Never posts or executes fixes."""
import argparse
from dataclasses import replace
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

from task_state import TaskStore
from candidate_rules import Candidate, clean_decision, load_candidates, BLOCKING_LABELS
from task_state import task_key, load_queue_state, SIGNALS, STAGES, ACTIONS
from contributions import cell, load_records, load_queue_records, require, validate_https_url as evidence
from pipeline_state import atomic_write_json, atomic_write_text, file_lock, read_json_object
from pr_state import ci_binding_error, load_pr_state
from repository_policy import ACCOUNT, INTERACTION_HOLDS
from pr_monitor import ci_failed

ROOT = Path(__file__).resolve().parents[1]
REVIEW_STATES = ("-", "APPROVED", "CHANGES_REQUESTED", "REVIEW_REQUIRED")


def date(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo else None
    except (AttributeError, ValueError):
        return None


def fresh(value, now, hours=24):
    parsed = date(value)
    return parsed is not None and timedelta(0) <= now - parsed <= timedelta(hours=hours)


def valid_key(key):
    task_key(key)


def load_queue(path):
    return _validate_queue_evidence(load_queue_state(path))


def _validate_queue_evidence(state):
    for section in ("issues", "prs"):
        for entry in state[section].values():
            if section == "issues":
                for signal in entry["signals"].values():
                    evidence(signal.get("source"))
            else:
                evidence(entry.get("source"))
    return state


def rank_candidates(candidates, state, store, cache, now, handled=None):
    rows, seen = [], set()
    merged = Counter(k.split('#')[0].lower() for k, v in cache.items()
                     if v.get("state") == "MERGED" and not v.get("query_error"))
    for candidate in candidates:
        require(isinstance(candidate.repo, str) and type(candidate.number) is int and candidate.number > 0,
                '候选编号/仓库格式错误')
        require(isinstance(candidate.title, str) and isinstance(candidate.labels, list)
                and all(isinstance(x, str) for x in candidate.labels), '候选标题/标签格式错误')
        require(all(type(getattr(candidate, name)) is bool for name in
                    ('is_bug', 'issue_unknown', 'pr_unknown', 'cmt_unknown')), '候选检查状态必须为布尔值')
        key = candidate.key.lower()
        valid_key(key)
        if key.split('/')[0] == ACCOUNT.lower():
            continue
        if key in seen:
            continue
        seen.add(key)
        entry = state["issues"].get(key, {})
        decision = store.decision(key, now, handled=handled, issue=entry)
        stage, completed = decision['stage'], decision['reason']
        screening = clean_decision(replace(candidate, issue_unknown=False, pr_unknown=False, cmt_unknown=False),
                                   store, decision=decision, records=cache, now=now)
        ok, reason = screening['eligible'], screening['reason']
        capacity_blocked = screening['gate'] == 'capacity'
        unknown = candidate.issue_unknown or candidate.pr_unknown or candidate.cmt_unknown
        reasons, missing = [], []
        score = 0
        capacity = screening.get('capacity')
        if capacity and capacity['allowed'] and capacity['count'] >= 2:
            reasons.append(capacity['reason'])
        if completed:
            missing.append("已处理: " + completed + "；需显式重开")
        if not ok:
            missing.append(reason)
        if unknown:
            missing.append("尚未完成共享核验；运行 monitor_round.py --pending")
        if set(l.lower() for l in candidate.labels) & BLOCKING_LABELS:
            missing.append("标签尚未就绪")
        if stage in {"stopped", "submitted"}:
            missing.append("已退出/提交，需显式重开")
        if stage == "deferred" and (not date(entry.get("retry_at")) or date(entry['retry_at']) > now):
            missing.append("延期未到复查时间")
        if not fresh(candidate.checked_at, now):
            missing.append("扫描过期或缺少核验时间，重扫")
        sources = []
        for name, points in (("policy", 0), ("collision", 0), ("intent", 20),
                             ("reproduced", 15), ("testable", 10), ("small", 10)):
            signal = entry.get("signals", {}).get(name, {})
            if signal.get("value") is True and fresh(signal.get("at"), now):
                score += points
                reasons.append(name + " 已核验")
                sources.append(signal['source'])
            elif name in {"policy", "collision", "intent"}:
                missing.append(name + " 未通过或已过期")
        if fresh(candidate.createdAt, now, 48):
            score += 5
            reasons.append("48 小时内新 issue +5")
        if merged[candidate.repo.lower()]:
            score += 5
            reasons.append("本地缓存有同仓合并经验 +5（非合并概率）")
        if entry.get("signals", {}).get("testable", {}).get("value") is False:
            missing.append("已确认不可测试：延期或退出；环境变化后重新核验 testable 才能恢复")
        if stage == "fixing":
            for name in ("reproduced", "testable"):
                signal = entry.get("signals", {}).get(name, {})
                if not signal.get("value") or not fresh(signal.get("at"), now):
                    missing.append(name + " 需核验后再修复")
        hidden = stage in {"stopped", "submitted"} or (stage == "deferred" and any("延期" in m for m in missing))
        visible_stage = ('capacity_hold' if capacity['status'] == 'HOLD' else 'capacity_unknown') if capacity_blocked else stage
        rows.append({"kind": "issue", "key": key, "score": score, "ready": not missing,
                     "hidden": bool(completed) or hidden or (not ok and not capacity_blocked),
                     "stage": visible_stage, "contribution_kind": candidate.kind, "reasons": reasons,
                     "sources": sorted(set(sources)),
                     "missing": missing, "next": "; ".join(missing) if missing else
                     ("继续修复；超预算重新评估；提交前再次终检" if stage == "fixing" else "限时 20 分钟复现探路")})
    return rows


def feedback_fingerprint(items):
    def encoded(value):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    canonical = [encoded(dict(item, sources=sorted(item['sources'], key=encoded))) for item in items]
    return hashlib.sha256(encoded(sorted(canonical)).encode('utf-8')).hexdigest()


def observation_ack(pr, now=None, feedback_items=()):
    """A judgement covers a complete, fresh observation, not an aggregate count."""
    now = now or datetime.now(timezone.utc)
    if (pr.get("state") != "OPEN" or pr.get("query_error") or ci_binding_error(pr)
            or not fresh(pr.get("checked_at"), now) or not fresh(pr.get("ci_checked_at"), now)
            or not date(pr.get("updatedAt"))
            or pr.get("reviewDecision") not in REVIEW_STATES):
        return None
    return {"version": 3, "feedback_fingerprint": feedback_fingerprint(feedback_items),
            "merge_conflict": pr.get("mergeable") == "CONFLICTING",
            **{key: pr.get(key) for key in
            ("updatedAt", "reviewDecision", "headRefOid", "ci", "ci_head_oid", "ci_fingerprint")}}


def pr_tasks(cache, state, records, now, record_errors=()):
    rows = []
    known = {f"{r['repo']}#{r['pr']}".lower(): r for r in records if r.get("pr")}
    invalid = {entry['pr_key']: entry['error'] for entry in record_errors if entry.get('pr_key')}
    unmapped_errors = any(not entry.get('pr_key') for entry in record_errors)
    for key, pr in cache.items():
        if pr.get("state") != "OPEN" and not (pr.get("state") is None and pr.get("query_error")):
            continue
        saved_action = state['prs'].get(key, {})
        feedback_items = known[key]['feedback']['items'] if key in known else []
        current_ack = None if key in invalid or unmapped_errors else observation_ack(pr, now, feedback_items)
        saved_ack = saved_action.get("ack")
        if isinstance(saved_ack, dict):
            # Older judgements did not record conflicts; retain them only without one.
            saved_ack = {"merge_conflict": False, **saved_ack}
        # All manual categories expire on new observations, including discussion.
        action = saved_action if current_ack is not None and saved_ack == current_ack else {}
        reason, score = action.get("note", ""), ACTIONS.get(action.get("action"), 0)
        uncertainty = []
        if key in invalid:
            uncertainty.append('贡献记录异常，先修复证据: ' + invalid[key])
        elif unmapped_errors and saved_action:
            uncertainty.append('存在无法关联 PR 的损坏贡献记录，旧反馈确认暂不可用')
        if pr.get("query_error") or not fresh(pr.get("checked_at"), now):
            uncertainty.append("状态过期或查询失败，先刷新 PR 状态")
        if pr.get("reviewDecision") not in REVIEW_STATES:
            uncertainty.append("评审状态缺失或未知，先刷新 PR 状态")
        ci_error = ci_binding_error(pr)
        if ci_error:
            uncertainty.append(ci_error + "；运行 monitor_oss.py 刷新 CI")
        elif not fresh(pr.get("ci_checked_at"), now):
            uncertainty.append("CI 观测过期或缺少时间，运行 monitor_oss.py 刷新")
        uncertain = bool(uncertainty)
        if action.get("action") in {"wait", "done"} and not uncertain:
            continue
        if not score:
            if pr.get("mergeable") == "CONFLICTING":
                score, reason = 90, "存在已确认的合并冲突；同步分支后重新验证"
            elif pr.get("reviewDecision") == "CHANGES_REQUESTED":
                score, reason = 85, "评审状态要求修改；先读原文确认作者与范围"
            elif ci_failed(pr.get("ci", "")):
                score, reason = 70, "CI 有失败/错误/未知，先判断是否由本 PR 引入"
            elif feedback_items:
                score, reason = 15, "贡献记录有反馈，需区分人工意见与机器人提示"
            elif saved_action:
                score, reason = 15, "观测已变化或旧分类缺少有效依据，重新确认 PR 待办"
            elif not uncertain:
                continue
        if uncertain:
            score, reason = 10, "；".join(uncertainty)
        hold = INTERACTION_HOLDS.get(key.split('#')[0].lower())
        if hold:
            score = 0
            reason = hold + ("；状态也需只读刷新" if uncertain else "")
        rows.append({"kind": "pr", "key": key, "score": score, "ready": not bool(uncertain),
                     "hidden": False, "stage": action.get("action", "review"),
                     "reasons": [reason], "missing": uncertainty, "next": reason,
                     "source": action.get("source")})
        if hold:
            rows[-1].update(ready=False, stage="policy_hold", missing=[hold])
    return rows


def weekly(cache, state, now):
    start = now - timedelta(days=7)
    def in_week(value):
        parsed = date(value)
        return parsed is not None and start <= parsed <= now
    successful = {k: v for k, v in cache.items() if not v.get('query_error')}
    cohort = {k: v for k, v in successful.items() if in_week(v.get('createdAt'))}
    counts = Counter(v.get('state') for v in cohort.values())
    merged = sum(v.get('state') == 'MERGED' and in_week(v.get('mergedAt')) for v in successful.values())
    missing = sum(v.get('state') == 'MERGED' and not date(v.get('mergedAt')) for v in successful.values())
    events = [e for section in ('issues', 'prs') for key, entry in state[section].items()
              if key.split('/')[0].lower() != ACCOUNT.lower()
              for e in entry['events'] if in_week(e['at'])]
    minutes = sum(e['minutes'] for e in events)
    exits = Counter(e.get('note', '') for e in events if e.get('stage') == 'stopped')
    decided = counts['MERGED'] + counts['CLOSED']
    return ["# 每周贡献产出", "", f"滚动七天（UTC）：{start.isoformat()} — {now.isoformat()}", "",
            f"有合并日期的本周合并：{merged}；已合并但缺日期：{missing}（不猜测归属周）。",
            f"本周提交批次：{len(cohort)}；已合并 {counts['MERGED']}；关闭未合并 {counts['CLOSED']}；等待 {counts['OPEN']}。",
            f"已决样本合并率：{counts['MERGED'] / decided:.0%}（{counts['MERGED']}/{decided}，小样本不外推）" if decided else "已决样本合并率：暂无已决样本。",
            f"缺提交日期：{sum(not date(v.get('createdAt')) for v in successful.values())}；查询失败排除：{len(cache) - len(successful)}。",
            f"本周已记录实际工时：{minutes} 分钟；不能当成完整工时或据此计算每个合并 PR 成本。", "",
            "退出原因：" + ("；".join(f"{k}: {v}" for k, v in exits.items()) or "暂无记录"), "",
            "范围仅为 pr_state.json 跟踪样本；等待中的 PR 不计失败。created_at 台账导入时间不作为提交时间。",
            "试运行期间记录每次实际投入；七天后检查候选误报、重复劳动及探路耗时，再调整分值。"]


def refresh(root=ROOT, limit=50):
    require(type(limit) is int and limit >= 0, "展示上限必须为非负整数，0 表示全部")
    now = datetime.now(timezone.utc)
    with file_lock(root / 'work_queue_view.json'):
        store = TaskStore(root=root)
        state = _validate_queue_evidence(store.queue)
        candidates = load_candidates(root / 'round_candidates.json')
        existing = {c.key.lower() for c in candidates}
        inbox = read_json_object(root / 'tools/fresh_candidates.json')
        candidates += [Candidate(**v) for k, v in inbox.items() if k.lower() not in existing]
        cache = {k.lower(): v for k, v in load_pr_state(root / 'pr_state.json', ()).items()
                 if k.split('/')[0].lower() != ACCOUNT.lower()}
        records, record_errors = load_queue_records(root)
        rows = rank_candidates(candidates, state, store, cache, now, store.handled)
        rows += pr_tasks(cache, state, records, now, record_errors)
        rows.sort(key=lambda r: (r['hidden'], not r['ready'], -r['score'], r['key']))
        lines = ['# 贡献工作队列', '', f'生成时间：{now.isoformat()}', '',
                 '分数是调度规则，不是合并概率；缺关键核验时只能进入核验队列。来源核验有效期 24 小时。',
                 '仅调度外部仓库贡献，排除当前账号自有仓库；反馈分类可用 pr-action 修正。',
                 '探路预算 20 分钟；实际修复预算按任务评估。提交前仍执行 RULES.md 五查、终检和并发限制。', '',
                 f"缓存 OPEN 数：{sum(v.get('state') == 'OPEN' for v in cache.values())}（仅跟踪范围；不是实时提交许可）。", '',
                 '| 类型 | 任务 | 阶段 | 分数 | 下一步 | 依据 |', '| --- | --- | --- | --- | --- | --- |']
        visible = [r for r in rows if not r['hidden']]
        displayed = visible[:limit] if limit else visible
        for row in displayed:
            repo, number = row['key'].split('#')
            url = f"https://github.com/{repo}/{'pull' if row['kind'] == 'pr' else 'issues'}/{number}"
            label = {'capacity_hold': '待名额', 'capacity_unknown': '需核验'}.get(
                row['stage'], row['stage'] if row['ready'] or row['stage'] == 'policy_hold' else '先核验')
            lines.append(f"| {row['kind']} | [{row['key']}]({url}) | {cell(label)} | {row['score']} | {cell(row['next'])} | {cell('; '.join(row['reasons']) or '无已核验加分')} |")
        lines += ['', f"展示 {len(displayed)}/{len(visible)} 个可见任务；全部结果见 work_queue_view.json；refresh --limit 0 展示全部。", f"隐藏已退出/延期/过滤任务：{len(rows) - len(visible)}；明细见 work_queue_view.json。",
                  '候选不在本轮快照时保留其历史状态，但不继续推荐。']
        if record_errors:
            lines += ['', '贡献记录异常（不阻断其他任务；异常记录不作为已核验证据）：']
            lines += [f"- {cell(entry['record'])}: {cell(entry['error'])}" for entry in record_errors]
        lines += ['', '队列仅校验记录结构、证据路径及用于反馈确认的来源；提交前仍须执行完整证据检查。']
        atomic_write_json(root / 'work_queue_view.json', {"generated_at": now.isoformat(), "tasks": rows,
                                                       "record_errors": record_errors})
        atomic_write_text(root / 'WORK_QUEUE.md', '\n'.join(lines) + '\n')
        atomic_write_text(root / 'WEEKLY_CONTRIBUTIONS.md', '\n'.join(weekly(cache, state, now)) + '\n')
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    refresh_parser = sub.add_parser('refresh')
    refresh_parser.add_argument('--limit', type=int, default=50, help='报告行数，0 表示全部')
    assess = sub.add_parser('assess', help='录入证据检查结果；不代表真人审阅')
    assess.add_argument('key')
    assess.add_argument('signal', choices=sorted(SIGNALS))
    assess.add_argument('value', choices=['yes', 'no'])
    assess.add_argument('--source', required=True)
    stage = sub.add_parser('stage')
    stage.add_argument('key')
    stage.add_argument('stage', choices=sorted(STAGES))
    stage.add_argument('--retry-at')
    action = sub.add_parser('pr-action')
    action.add_argument('key')
    action.add_argument('action', choices=sorted(ACTIONS))
    action.add_argument('--source', required=True)
    for child in (assess, stage, action):
        child.add_argument('--note', required=True)
        child.add_argument('--minutes', type=int, default=0)
    args = parser.parse_args(argv)
    if args.command != 'refresh':
        valid_key(args.key)
        require(args.note.strip() and args.minutes >= 0, '需说明理由；工时不得为负')
        key = args.key.lower()
        with TaskStore(root=ROOT).transaction() as ledger:
            now = datetime.now(timezone.utc).isoformat()
            state = _validate_queue_evidence(ledger['queue'])
            event = {'at': now, 'minutes': args.minutes, 'note': args.note, 'command': args.command}
            if args.command == 'pr-action':
                evidence(args.source)
                entry = state['prs'].setdefault(key, {'events': []})
                entry.update(action=args.action, source=args.source, at=now, note=args.note)
                cache = {k.lower(): v for k, v in load_pr_state(ROOT / 'pr_state.json', ()).items()}
                record = next((r for r in load_records(ROOT)
                               if f"{r['repo']}#{r['pr']}".lower() == key), None)
                items = record['feedback']['items'] if record else []
                entry['ack'] = observation_ack(cache.get(key, {}), feedback_items=items)
                event.update(action=args.action, source=args.source)
            else:
                entry = state['issues'].setdefault(key, {'stage': 'new', 'signals': {}, 'events': [], 'first_seen': now})
                if args.command == 'assess':
                    evidence(args.source)
                    entry['signals'][args.signal] = {'value': args.value == 'yes', 'source': args.source, 'at': now, 'note': args.note}
                    event.update(signal=args.signal, value=args.value, source=args.source)
                else:
                    if args.stage == 'deferred':
                        require(date(args.retry_at) and date(args.retry_at) > date(now), '延期必须给出未来带时区的 --retry-at')
                    entry.update(stage=args.stage, retry_at=args.retry_at)
                    event['stage'] = args.stage
            entry['events'].append(event)
    try:
        rows = refresh(limit=args.limit) if args.command == 'refresh' else refresh()
    except (ValueError, OSError, RuntimeError) as exc:
        if args.command != 'refresh':
            raise RuntimeError('状态已保存，视图未刷新；用 refresh 重试，勿重复登记') from exc
        raise
    print(f"生成 WORK_QUEUE.md / WEEKLY_CONTRIBUTIONS.md；{len(rows)} 项（包含隐藏项）")


if __name__ == '__main__':
    main()
