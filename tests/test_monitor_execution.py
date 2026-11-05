"""Bounded PR queries and retry behavior; fake GitHub and temporary state only."""
import contextlib
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import monitor_oss as oss
import monitor_scope as scope


class MonitorExecutionTests(unittest.TestCase):
    def test_four_concurrent_queries_preserve_order_and_partial_results(self):
        keys = [f"owner/repo#{i}" for i in range(1, 10)]
        for module in (oss, scope):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                barrier = threading.Barrier(4, timeout=2)
                finished = {key: threading.Event() for key in keys[:4]}
                activity_lock = threading.Lock()
                active = maximum = 0
                queried = []

                def fetch(key):
                    nonlocal active, maximum
                    with activity_lock:
                        active += 1
                        maximum = max(maximum, active)
                        queried.append(key)
                    try:
                        if key in finished:
                            barrier.wait()
                            index = keys.index(key)
                            if index < 3 and not finished[keys[index + 1]].wait(timeout=2):
                                raise AssertionError("Earlier query did not finish")
                            finished[key].set()
                        if key == keys[4]:
                            return {"state": "QUERY_ERROR", "_err": "offline",
                                    "mergeable": "-", "reviewDecision": "-", "ci": "-", "title": ""}
                        return {"state": "OPEN", "mergeable": "MERGEABLE",
                                "reviewDecision": "-", "ci": "no-checks", "title": key}
                    finally:
                        with activity_lock:
                            active -= 1

                loader = "load_keys" if module is oss else "load_state_keys"
                with patch.object(module, "CANONICAL", str(root / "pr_state.json")), \
                        patch.object(module, "REPORT", str(root / "PR_STATUS.md")), \
                        patch.object(module, "STATE", str(root / "STATE.md")), \
                        patch.object(module, "LEGACY_PATHS", ()), \
                        patch.object(module, loader, return_value=dict.fromkeys(reversed(keys))), \
                        patch.object(module, "fetch", side_effect=fetch), \
                        patch.object(oss, "audit_scope"), \
                        patch.object(module, "ThreadPoolExecutor", wraps=ThreadPoolExecutor, create=True) as pool, \
                        contextlib.redirect_stdout(io.StringIO()):
                    status = module.main()

                self.assertEqual(pool.call_count, 1)
                self.assertEqual(pool.call_args.kwargs["max_workers"], 4)
                self.assertEqual(maximum, 4)
                self.assertCountEqual(queried, keys)
                self.assertEqual(status, 1)
                saved = json.loads((root / "pr_state.json").read_text(encoding="utf-8"))
                self.assertEqual(list(saved), keys)
                self.assertEqual(saved[keys[4]]["query_error"], "offline")
                self.assertTrue(all(saved[key]["state"] == "OPEN" for key in keys if key != keys[4]))

    def test_retry_sleeps_only_between_attempts_and_skips_missing_executable(self):
        response = json.dumps({"state": "OPEN", "statusCheckRollup": []})
        cases = [([RuntimeError("offline"), response], "OPEN", 2, 1),
                 ([RuntimeError("offline"), RuntimeError("offline")], "QUERY_ERROR", 2, 1),
                 ([FileNotFoundError("gh missing")], "QUERY_ERROR", 1, 0)]
        for module in (oss, scope):
            for responses, state, calls, sleeps in cases:
                with self.subTest(module=module.__name__, responses=responses), \
                        patch.object(module, "gh", side_effect=responses) as gh, \
                        patch("time.sleep") as sleep:
                    self.assertEqual(module.fetch("owner/repo#1")["state"], state)
                    self.assertEqual(gh.call_count, calls)
                    self.assertEqual(sleep.call_count, sleeps)
                    if sleeps:
                        sleep.assert_called_once_with(2)


if __name__ == "__main__":
    unittest.main()
