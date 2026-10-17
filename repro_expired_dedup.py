"""Offline public-API reproduction for mem0 issue #7612.

Real local Qdrant (on-disk) and SQLite; LLM and embedding providers are
deterministic test doubles. The mem0 source tree is NOT modified.

Run from the mem0-src checkout:
    E:/zcode-PR/.venv312/Scripts/python.exe E:/zcode-PR/repro_expired_dedup.py --api sync --case expired
"""

import argparse
import asyncio
import inspect
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from mem0 import AsyncMemory, Memory
from mem0.embeddings.base import EmbeddingBase

FACT = "User likes hiking"
EXPIRED = "2000-01-01"
FUTURE = "2999-01-01"


class FixedEmbeddings(EmbeddingBase):
    def embed(self, text, memory_action=None):
        return [1.0, 0.0, 0.0]


class ExtractFact:
    def __init__(self):
        self.prompts = []

    def generate_response(self, messages, **kwargs):
        self.prompts.append(messages[1]["content"])
        return json.dumps({"memory": [{"text": FACT}]})


async def invoke(memory, method, *args, **kwargs):
    result = getattr(memory, method)(*args, **kwargs)
    return await result if inspect.isawaitable(result) else result


async def run(api, case):
    llm = ExtractFact()
    cls = Memory if api == "sync" else AsyncMemory
    first_expiry = FUTURE if case == "active" else EXPIRED
    second_infer = case != "raw"
    with tempfile.TemporaryDirectory(prefix="mem0-expired-dedup-") as temporary:
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "path": str(Path(temporary) / "qdrant"),
                    "embedding_model_dims": 3,
                },
            },
            "history_db_path": str(Path(temporary) / "history.db"),
        }
        with (
            patch("mem0.memory.main.EmbedderFactory.create", return_value=FixedEmbeddings()),
            patch("mem0.memory.main.LlmFactory.create", return_value=llm),
        ):
            memory = cls.from_config(config)
            try:
                first = await invoke(memory, "add", FACT, user_id="alice", expiration_date=first_expiry)
                before = await invoke(memory, "get_all", filters={"user_id": "alice"})
                second = await invoke(
                    memory, "add", FACT, user_id="alice", expiration_date=FUTURE, infer=second_infer
                )
                after = await invoke(memory, "get_all", filters={"user_id": "alice"})
                searchable = await invoke(memory, "search", "hiking", filters={"user_id": "alice"})
                stored = await invoke(memory, "get_all", filters={"user_id": "alice"}, show_expired=True)
                existing_context = (
                    llm.prompts[-1].split("## Existing Memories")[1].split("## New Messages")[0]
                    if second_infer
                    else ""
                )
                print(f"api={api} case={case}")
                print("first ADD:", len(first["results"]))
                print("visible before:", len(before["results"]))
                print("second ADD:", len(second["results"]))
                print("visible after:", len(after["results"]))
                print("searchable after:", len(searchable["results"]))
                print("stored expirations:", sorted(item["expiration_date"] for item in stored["results"]))
                print("fact in second Existing Memories:", FACT in existing_context if second_infer else "not called")

                assert len(first["results"]) == 1
                assert len(before["results"]) == (1 if case == "active" else 0)
                assert len(after["results"]) == 1, "An expired copy suppressed the new unexpired memory"
                assert len(searchable["results"]) == 1
                assert len(second["results"]) == (0 if case == "active" else 1)
                if case == "expired":
                    assert FACT not in existing_context, "Expired memory was supplied as an existing active fact"
            finally:
                memory.close()
                memory.vector_store.client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", choices=["sync", "async"], default="sync")
    parser.add_argument("--case", choices=["expired", "active", "raw"], default="expired")
    arguments = parser.parse_args()
    asyncio.run(run(arguments.api, arguments.case))
