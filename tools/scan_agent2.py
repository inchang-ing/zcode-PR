#!/usr/bin/env python
"""Agent / LLM 生态侦察扫描器 —— 池 G(扩池:基础设施 / 向量库客户端 / 评测 / 语音 agent / 数据摄取)。

用法: python scan_agent2.py [hours]
输出: 按新鲜度升序的候选列表(无 assignee、非 PR、评论 <=2)
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

GH = r"C:\Program Files\GitHub CLI\gh.exe"

# 池 G:agent 生态的外围基础设施与前/后处理,竞争度通常低于核心框架
G = [
    # 评测 / 护栏 / 可观测
    "confident-ai/deepeval",
    "truera/trulens",
    "guardrails-ai/guardrails",
    "NVIDIA/NeMo-Guardrails",
    "athina-ai/athina-evals",
    "UKGovernmentBEIS/inspect_ai",
    "EleutherAI/lm-evaluation-harness",
    "openai/evals",
    "huggingface/lighteval",
    "parea-ai/parea-sdk-py",
    "Arize-ai/openinference",
    "whylabs/whylogs",
    "deepchecks/deepchecks",
    "cleanlab/cleanlab",
    "wandb/wandb",
    # 向量库 / 检索客户端
    "qdrant/qdrant-client",
    "weaviate/weaviate-python-client",
    "milvus-io/pymilvus",
    # 数据摄取 / RAG 前置
    "unstructured-io/unstructured",
    "docling-project/docling",
    "argilla-io/argilla",
    "llmware-ai/llmware",
    "embedchain/embedchain",
    "run-llama/llama_parse?/skip",
    # 语音 / 实时 agent
    "daily-co/pipecat",
    "vocodedev/vocode-python",
    "bolna-ai/bolna",
    # 网关 / 编排 SDK
    "portkey-ai/portkey-python",
    "hegel-ai/promptic",
    "lastmile-ai/mcp-agent",
    "i-am-bee/beeai-framework",
    "mozilla-ai/any-agent",
    "gpt-engineer-org/gpt-engineer",
    # 训练 / 推理基础设施(纯 Python 部分)
    "huggingface/accelerate",
    "huggingface/setfit",
    # 交互 / 聊天 UI(Python)
    "chainlit/chainlit",
    "gradio-app/gradio",
]

NOISE = ("ScreenContextAgent",)


def fetch(repo, since_iso):
    url = f"repos/{repo}/issues?state=open&since={since_iso}&sort=created&direction=desc&per_page=25"
    try:
        r = subprocess.run([GH, "api", url], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return repo, None
        return repo, json.loads(r.stdout)
    except Exception:
        return repo, None


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    repos = [r for r in G if "/skip" not in r]

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    out = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for repo, data in ex.map(lambda r: fetch(r, since_iso), repos):
            if data is None:
                continue
            for it in data:
                if "pull_request" in it:
                    continue
                if it.get("assignee") or it.get("assignees"):
                    continue
                if it.get("comments", 0) > 2:
                    continue
                title = it.get("title", "")
                if any(n in title for n in NOISE):
                    continue
                created = datetime.strptime(it["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                age = (now - created).total_seconds() / 3600.0
                if age > hours:
                    continue
                out.append((age, repo, it["number"], it.get("comments", 0), title))

    out.sort()
    print(f"# agent 池G 扫描 {now.strftime('%Y-%m-%d %H:%M')} UTC | 窗口 {hours}h | 仓库 {len(repos)} | 候选 {len(out)}")
    for age, repo, num, nc, title in out:
        print(f"{age:6.2f}h  {repo}#{num}  [c{nc}]  {title[:95]}")


if __name__ == "__main__":
    main()
