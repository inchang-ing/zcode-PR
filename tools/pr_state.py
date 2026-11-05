"""Shared PR observations. JSON is authoritative; Markdown is a generated view."""
from datetime import datetime, timezone
import html
from pathlib import Path
import re

from pipeline_state import atomic_write_json, atomic_write_text, read_json_object

ROOT = Path(__file__).resolve().parents[1]  # 仓库根(本文件在 tools/)
PR_STATE_PATH = ROOT / "pr_state.json"
PR_STATUS_PATH = ROOT / "PR_STATUS.md"
LEGACY_PATHS = (ROOT / ".trash" / "scope_baseline.json",
                ROOT / ".trash" / "scope_oss_baseline.json")
VALID_STATES = {"OPEN", "CLOSED", "MERGED"}
CI_FIELDS = ("ci", "ci_head_oid", "ci_fingerprint", "ci_checked_at")


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ci_binding_error(record):
    """CI from an older/unknown head is historical evidence, never current success."""
    ci = record.get("ci")
    if ci is None:
        return "尚未查询 CI"
    if not isinstance(ci, str) or (ci != "no-checks" and not re.fullmatch(
            r"\d+✓/\d+✗/\d+…/\d+ERR/\d+SKIP/\d+UNKNOWN", ci)):
        return "CI 结果缺少完整结构，需重新查询"
    if any(int(n) for n in re.findall(r"(\d+)UNKNOWN", ci)):
        return "CI 含未知结果，需核验"
    head, ci_head = record.get("headRefOid"), record.get("ci_head_oid")
    if not all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) for value in (head, ci_head)):
        return "CI 未绑定有效提交，当前版本未验证"
    if head != ci_head:
        return "提交已变化，当前版本 CI 未验证"
    fingerprint = record.get("ci_fingerprint")
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        return "CI 检查明细缺失或无效，需重新查询"
    return ""


def normalize_pr_records(records):
    """Use one identity per PR; resolve old aliases only with ordered evidence."""
    groups = {}
    for key, record in records.items():
        if not isinstance(key, str) or not isinstance(record, dict):
            raise ValueError("Expected PR identity and record object")
        if record.get("state") not in (*VALID_STATES, None, "QUERY_ERROR"):
            raise ValueError(f"Invalid PR state for {key}")
        groups.setdefault(key.lower(), []).append(record)
    normalized = {}
    for key, aliases in groups.items():
        if all(record == aliases[0] for record in aliases):
            normalized[key] = dict(aliases[0])
            continue
        if (any(record.get("state") == "QUERY_ERROR" for record in aliases)
                and any(record.get("state") != "QUERY_ERROR" for record in aliases)):
            raise ValueError(f"Ambiguous PR aliases for {key}: mixed successful and failed query observations")

        def timestamp(value):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    return parsed
            except (AttributeError, ValueError):
                pass
            raise ValueError(f"Ambiguous PR aliases for {key}: missing or invalid observation time")

        successful = [record for record in aliases if record.get("state") in VALID_STATES]
        candidates = successful or aliases
        ordered = sorted(((timestamp(record.get("checked_at") if successful else
                                     record.get("query_error_at") or record.get("checked_at")), record)
                          for record in candidates), key=lambda item: item[0])
        merged, previous_time, previous_payload = {}, None, None
        for observed_at, record in ordered:
            payload = {field: value for field, value in record.items()
                       if field not in {"query_error", "query_error_at"}}
            comparable = {field: value for field, value in payload.items()
                          if field != "checked_at" and field not in CI_FIELDS}
            if observed_at == previous_time and comparable != previous_payload:
                raise ValueError(f"Ambiguous PR aliases for {key}: conflicting observations at the same time")
            merged.update(payload)
            previous_time, previous_payload = observed_at, comparable

        errors = sorted(((timestamp(record.get("query_error_at")), record["query_error"],
                          record.get("query_error_at")) for record in aliases if record.get("query_error")),
                        key=lambda item: item[0])
        if errors:
            error_at, message, original_time = errors[-1]
            if (successful and error_at == previous_time
                    or any(at == error_at and text != message for at, text, _ in errors)):
                raise ValueError(f"Ambiguous PR aliases for {key}: conflicting error and recovery times")
            if not successful or error_at > previous_time:
                merged.update(query_error=message, query_error_at=original_time)
        ci_groups = [{field: record[field] for field in CI_FIELDS if field in record}
                     for record in aliases if any(field in record for field in CI_FIELDS)]
        if ci_groups:
            selected_ci = ci_groups[0]
            if any(group != selected_ci for group in ci_groups):
                ci_ordered = sorted(((timestamp(group.get("ci_checked_at")), group) for group in ci_groups),
                                    key=lambda item: item[0])
                previous_ci_time, previous_ci = None, None
                for checked_at, group in ci_ordered:
                    comparable = {field: value for field, value in group.items() if field != "ci_checked_at"}
                    if checked_at == previous_ci_time and comparable != previous_ci:
                        raise ValueError(f"Ambiguous PR aliases for {key}: conflicting CI at the same time")
                    previous_ci_time, previous_ci = checked_at, comparable
                selected_ci = ci_ordered[-1][1]
            for field in CI_FIELDS:
                merged.pop(field, None)
            merged.update(selected_ci)
        normalized[key] = merged
    return normalized


def _validate_records(records, path):
    for key, value in records.items():
        if not isinstance(value, dict):
            raise ValueError(f"Expected PR record object for {key} in {path}")
        if value.get("state") not in (*VALID_STATES, None):
            raise ValueError(f"Invalid PR state for {key} in {path}")
    return normalize_pr_records(records)


def load_pr_state(path=PR_STATE_PATH, legacy_paths=LEGACY_PATHS):
    """Migrate legacy snapshots in memory only when canonical state is absent."""
    if Path(path).exists():
        return _validate_records(read_json_object(path), path)
    merged = {}
    for legacy in legacy_paths:
        for key, value in read_json_object(legacy).items():
            if not isinstance(value, dict):
                raise ValueError(f"Expected PR record object for {key} in {legacy}")
            if value.get("state") in VALID_STATES:
                merged.setdefault(key, {}).update({k: v for k, v in value.items() if k != "_err"})
            elif value.get("state") == "QUERY_ERROR":
                merged.setdefault(key, {})["query_error"] = value.get("_err") or "Legacy query failed"
            else:
                raise ValueError(f"Invalid legacy PR state for {key} in {legacy}")
    return _validate_records(merged, path)


def merge_observations(previous, observations):
    """Keep fields an entry point did not fetch, and keep successful data on errors."""
    merged = normalize_pr_records(previous)
    for key, observation in normalize_pr_records(observations).items():
        record = merged.setdefault(key, {})
        queried_at = observation.get("checked_at") or utc_now()
        if observation.get("state") not in VALID_STATES:
            record["query_error"] = observation.get("_err") or "PR query failed"
            record["query_error_at"] = queried_at
            continue
        record.update({k: v for k, v in observation.items()
                       if k not in {"_err", "query_error", "query_error_at"}})
        record["checked_at"] = queried_at
        record.pop("query_error", None)
        record.pop("query_error_at", None)
    return merged


def _cell(value):
    return html.escape(str(value if value is not None else "-"), quote=False).replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def render_pr_status(records, generated_at=None):
    records = normalize_pr_records(records)
    generated_at = generated_at or utc_now()
    lines = ["# PR 状态", "", f"生成时间：{generated_at}", "",
             "自动生成的只读展示，请勿手动编辑。权威数据：`pr_state.json`；跟踪范围仍由 `STATE.md` 选择。",
             "`checked_at` 是最后成功核验时间；查询失败时保留此前状态，错误和失败时间单独显示。旧基线没有核验时间时显示“未记录”。",
             "保留的 CI / 标题可能来自另一入口的较早成功观测；CI 必须与当前提交相符，CI 核验时间单独显示。", "",
             "| PR | 状态 | 评审 | 合并状态 | CI | 最后成功核验 | 查询错误（时间） | 标题 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for key in sorted(records):
        record = records[key]
        match = re.fullmatch(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)", key)
        label = (f"[{_cell(key)}](https://github.com/{match[1]}/pull/{match[2]})"
                 if match else _cell(key))
        error = record.get("query_error")
        if error:
            error = f"{error} ({record.get('query_error_at', '未记录')})"
        ci = record.get("ci", "未查询")
        binding_error = ci_binding_error(record)
        if binding_error:
            ci = f"未验证：{binding_error}（历史结果：{ci}）"
        ci = f"{ci}；CI 核验：{record.get('ci_checked_at', '未记录')}"
        cells = [record.get("state", "未核验"), record.get("reviewDecision", "-"),
                 record.get("mergeable", "-"), ci,
                 record.get("checked_at", "未记录"), error or "-", record.get("title", "-")]
        lines.append("| " + label + " | " + " | ".join(_cell(v) for v in cells) + " |")
    if not records:
        lines.extend(["", "暂无成功核验的 PR 记录。"])
    return "\n".join(lines) + "\n"


def write_pr_status(path=PR_STATE_PATH, report_path=PR_STATUS_PATH):
    """Generate the report from committed canonical data, never from a legacy view."""
    if not Path(path).exists():
        raise FileNotFoundError(f"Canonical PR state does not exist: {path}")
    atomic_write_text(report_path, render_pr_status(load_pr_state(path, ())))


def save_observations(path, previous, observations, report_path):
    """Caller holds the canonical lock across load, fetch and this write."""
    if not Path(path).exists() and not any(v.get("state") in VALID_STATES for v in observations.values()):
        return False
    atomic_write_json(path, merge_observations(previous, observations))
    write_pr_status(path, report_path)
    return True
