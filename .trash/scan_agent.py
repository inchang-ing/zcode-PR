#!/usr/bin/env python
"""Agent / LLM 生态侦察扫描器(新方向主扫描器)。

用法: python scan_agent.py [hours] [pool|all]
  pool: core(允许外部 PR 的主攻池) | watch(政策受限,仅监控) | all
输出: 按新鲜度升序的候选列表(无 assignee、非 PR、评论 <=2)
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

GH = r"C:\Program Files\GitHub CLI\gh.exe"

# 允许外部 PR / 无指派门禁(主攻池)
CORE = [
    "agno-agi/agno",
    "crewAIInc/crewAI",
    "browser-use/browser-use",
    "google/adk-python",
    "langflow-ai/langflow",
    "microsoft/semantic-kernel",
    "run-llama/llama_index",
    "langchain-ai/langchain",
    "langchain-ai/langgraph",
    "langchain-ai/langsmith-sdk",
    "camel-ai/camel",
    "geekan/MetaGPT",
    "OpenBMB/ChatDev",
    "modelscope/agentscope",
    "QwenLM/Qwen-Agent",
    "bytedance/deer-flow",
    "microsoft/graphrag",
    "deepset-ai/haystack",
    "langroid/langroid",
    "kyegomez/swarms",
    "OpenInterpreter/open-interpreter",
    "assafelovic/gpt-researcher",
    "mem0ai/mem0",
    "julep-ai/julep",
    "livekit/agents",
    "upsonic/Upsonic",
    "instructor-ai/instructor",
    "guidance-ai/guidance",
    "dottxt-ai/outlines",
    "jlowin/fastmcp",
    "modelcontextprotocol/servers",
    "explodinggradients/ragas",
    "chroma-core/chroma",
    "lancedb/lancedb",
    "paul-gauthier/aider",
    "SWE-agent/SWE-agent",
    "All-Hands-AI/OpenHands",
    "significant-gravitas/auto-gpt",
    "agentops-ai/agentops",
    "comet-ml/opik",
    "traceloop/openllmetry",
    "Arize-ai/phoenix",
    "langfuse/langfuse",
    "huggingface/trl",
    "huggingface/peft",
    "huggingface/huggingface_hub",
    "huggingface/tokenizers",
    "textualize/textual",
    "Textualize/rich",
    "prompt-toolkit/python-prompt-toolkit",
    "einsteinpy?/skip",
]

# 政策受限(只监控,不主动提交)
WATCH = [
    "openai/openai-python",
    "openai/openai-agents-python",
    "stanfordnlp/dspy",
    "modelcontextprotocol/python-sdk",
    "pydantic/pydantic-ai",
    "huggingface/smolagents",
    "BerriAI/litellm",
    "microsoft/autogen",
    "anthropics/anthropic-sdk-python",
    "googleapis/python-genai",
    "mistralai/client-python?/skip",
]

NOISE = ("ScreenContextAgent",)


def fetch(repo, since_iso):
    url = f"repos/{repo}/issues?state=open&since={since_iso}&sort=created&direction=desc&per_page=25"
    try:
        r = subprocess.run([GH, "api", url], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return repo, None, (r.stderr or "")[:80]
        return repo, json.loads(r.stdout), None
    except Exception as e:
        return repo, None, str(e)[:80]


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    which = sys.argv[2] if len(sys.argv) > 2 else "all"
    repos = {"core": CORE, "watch": WATCH, "all": CORE + WATCH}[which]
    repos = [r for r in repos if "/skip" not in r]

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    out = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for repo, data, err in ex.map(lambda r: fetch(r, since_iso), repos):
            if err or data is None:
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
    print(f"# agent 生态扫描 {now.strftime('%Y-%m-%d %H:%M')} UTC | 窗口 {hours}h | 仓库 {len(repos)} | 候选 {len(out)}")
    for age, repo, num, nc, title in out:
        print(f"{age:6.2f}h  {repo}#{num}  [c{nc}]  {title[:95]}")


if __name__ == "__main__":
    main()
