"""Local, explainable contribution scheduling. Never posts or executes fixes."""
import argparse
from dataclasses import replace
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

from auto_run import Candidate, DispatchedStore, is_clean, load_candidates
from contributions import cell, load_records, require, validate_https_url as evidence
from pipeline_state import atomic_write_json, atomic_write_text, file_lock, read_json_object
from pr_state import ci_binding_error, load_pr_state, utc_now
from repository_policy import ACCOUNT, INTERACTION_HOLDS
from monitor_oss import ci_failed
from vet import BLOCKING_LABELS

ROOT = Path(__file__).resolve().parents[1]
SIGNALS = {"policy", "collision", "intent", "reproduced", "testable", "small"}
STAGES = {"new", "probe", "fixing", "submitted", "stopped", "deferred"}
ACTIONS = {"small_fix": 100, "ci": 80, "discussion": 20, "wait": 0, "done": 0}
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
    require(isinstance(key, str) and re.fullmatch(r"[\w.-]+/[\w.-]+#[1-9]\d*", key, re.ASCII), "无效 owner/repo#编号")
    require(all(p not in {'.', '..'} for p in key.split('#')[0].split('/')), "无效仓库")


def load_queue(path):
    state = read_json_object(path)
    if not state:
        return {"version": 1, "issues": {}, "prs": {}}
    require(state.get("version") == 1, "不支持的队列版本")
    for section in ("issues", "prs"):
        require(isinstance(state.get(section), dict), "队列缺少对象: " + section)
        for key, entry in state[section].items():
            valid_key(key)
            require(key == key.lower() and isinstance(entry, dict), "无效队列记录")
            require(isinstance(entry.get("events"), list), "缺少事件列表")
            for event in entry["events"]:
                require(isinstance(event, dict) and date(event.get("at")), "无效事件时间")
                require(type(event.get("minutes")) is int and event["minutes"] >= 0, "无效工时")
            if section == "issues":
                require(entry.get("stage") in STAGES, "无效处理阶段")
                require(isinstance(entry.get("signals"), dict), "无效核验信息")
                for name, signal in entry["signals"].items():
                    require(name in SIGNALS and isinstance(signal, dict), "无效信号")
                    require(type(signal.get("value")) is bool and date(signal.get("at")), "无效信号值")
                    evidence(signal.get("source"))
            else:
                require(entry.get("action") in ACTIONS and date(entry.get("at")), "无效 PR 待办")
                evidence(entry.get("source"))
    return state


def rank_candidates(candidates, state, store, cache, now):
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
        if key in seen:
            continue
        seen.add(key)
        entry = state["issues"].get(key, {})
        stage = entry.get("stage", "new")
        ok, reason = is_clean(replace(candidate, issue_unknown=False, pr_unknown=False, cmt_unknown=False), store)
        unknown = candidate.issue_unknown or candidate.pr_unknown or candidate.cmt_unknown
        reasons, missing = [], []
        score = 0
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
        rows.append({"kind": "issue", "key": key, "score": score, "ready": not missing,
                     "hidden": hidden or not ok, "stage": stage, "reasons": reasons,
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
            **{key: pr.get(key) for key in
            ("updatedAt", "reviewDecision", "headRefOid", "ci", "ci_head_oid", "ci_fingerprint")}}


def pr_tasks(cache, state, records, now):
    rows = []
    known = {f"{r['repo']}#{r['pr']}".lower(): r for r in records if r.get("pr")}
    for key, pr in cache.items():
        if pr.get("state") != "OPEN" and not (pr.get("state") is None and pr.get("query_error")):
            continue
        saved_action = state['prs'].get(key, {})
        feedback_items = known[key]['feedback']['items'] if key in known else []
        current_ack = observation_ack(pr, now, feedback_items)
        # All manual categories expire on new observations, including discussion.
        action = saved_action if current_ack is not None and saved_action.get("ack") == current_ack else {}
        reason, score = action.get("note", ""), ACTIONS.get(action.get("action"), 0)
        uncertainty = []
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
            if pr.get("reviewDecision") == "CHANGES_REQUESTED":
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
    events = [e for section in ('issues', 'prs') for v in state[section].values() for e in v['events'] if in_week(e['at'])]
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


def refresh(root=ROOT):
    now = datetime.now(timezone.utc)
    path = root / 'work_queue.json'
    with file_lock(path):
        state = load_queue(path)
        candidates = load_candidates(root / 'round_candidates.json')
        existing = {c.key.lower() for c in candidates}
        inbox = read_json_object(root / 'tools/fresh_candidates.json')
        candidates += [Candidate(**v) for k, v in inbox.items() if k.lower() not in existing]
        cache = {k.lower(): v for k, v in load_pr_state(root / 'pr_state.json', ()).items()
                 if k.split('/')[0].lower() != ACCOUNT.lower()}
        records = load_records(root)
        rows = rank_candidates(candidates, state, DispatchedStore(str(root / 'dispatched.json')), cache, now)
        rows += pr_tasks(cache, state, records, now)
        rows.sort(key=lambda r: (r['hidden'], not r['ready'], -r['score'], r['key']))
        lines = ['# 贡献工作队列', '', f'生成时间：{now.isoformat()}', '',
                 '分数是调度规则，不是合并概率；缺关键核验时只能进入核验队列。来源核验有效期 24 小时。',
                 '仅调度外部仓库贡献，排除当前账号自有仓库；反馈分类可用 pr-action 修正。',
                 '探路预算 20 分钟；实际修复预算按任务评估。提交前仍执行 RULES.md 五查、终检和并发限制。', '',
                 f"缓存 OPEN 数：{sum(v.get('state') == 'OPEN' for v in cache.values())}（仅跟踪范围；不是实时提交许可）。", '',
                 '| 类型 | 任务 | 阶段 | 分数 | 下一步 | 依据 |', '| --- | --- | --- | --- | --- | --- |']
        visible = [r for r in rows if not r['hidden']]
        for row in visible:
            repo, number = row['key'].split('#')
            url = f"https://github.com/{repo}/{'pull' if row['kind'] == 'pr' else 'issues'}/{number}"
            label = row['stage'] if row['ready'] or row['stage'] == 'policy_hold' else '先核验'
            lines.append(f"| {row['kind']} | [{row['key']}]({url}) | {cell(label)} | {row['score']} | {cell(row['next'])} | {cell('; '.join(row['reasons']) or '无已核验加分')} |")
        lines += ['', f"隐藏已退出/延期/过滤任务：{len(rows) - len(visible)}；明细见 work_queue_view.json。",
                  '候选不在本轮快照时保留其历史状态，但不继续推荐。']
        atomic_write_json(root / 'work_queue_view.json', {"generated_at": now.isoformat(), "tasks": rows})
        atomic_write_text(root / 'WORK_QUEUE.md', '\n'.join(lines) + '\n')
        atomic_write_text(root / 'WEEKLY_CONTRIBUTIONS.md', '\n'.join(weekly(cache, state, now)) + '\n')
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('refresh')
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
        key, now = args.key.lower(), utc_now()
        path = ROOT / 'work_queue.json'
        with file_lock(path):
            state = load_queue(path)
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
            atomic_write_json(path, state)
    rows = refresh()
    print(f"生成 WORK_QUEUE.md / WEEKLY_CONTRIBUTIONS.md；{len(rows)} 项（包含隐藏项）")


if __name__ == '__main__':
    main()
