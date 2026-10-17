import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from auto_run import Candidate, DispatchedStore, is_clean
from pipeline_state import atomic_write_json, file_lock

spec = importlib.util.spec_from_file_location("filter_cands", ROOT / "work/filter_cands.py")
filter_cands = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filter_cands)


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.json"

    def test_incomplete_write_keeps_previous_snapshot(self):
        atomic_write_json(self.path, {"old": "完整"})
        with patch("pipeline_state.os.replace", side_effect=PermissionError("locked")):
            with self.assertRaises(PermissionError):
                atomic_write_json(self.path, {"new": 1})
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), {"old": "完整"})
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_invalid_json_is_not_silently_reset(self):
        self.path.write_text('{"broken":', encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            DispatchedStore(self.path)
        self.assertEqual(self.path.read_text(), '{"broken":')

    def test_stale_store_does_not_overwrite_another_update(self):
        first, second = DispatchedStore(self.path), DispatchedStore(self.path)
        first.mark("owner/repo#1", "needs_repro")
        second.mark("owner/repo#2", "dropped", reason="already claimed")
        self.assertEqual(set(DispatchedStore(self.path).data), {"owner/repo#1", "owner/repo#2"})

    def test_terminal_and_retryable_states_have_same_filter_semantics(self):
        store = DispatchedStore(self.path)
        candidates = []
        statuses = ["needs_repro", "repro_failed", "dropped", "pr_opened", "closed", "merged"]
        for index, status in enumerate(statuses, 1):
            candidate = Candidate("owner/repo", index, "Crash in parser", "https://example.test", is_bug=True)
            candidates.append(candidate)
            store.mark(candidate.key, status)
        actual = filter_cands.fresh_candidates(candidates, store)
        self.assertEqual([c.number for c in actual], [1, 2])
        self.assertEqual(actual, [c for c in candidates if is_clean(c, store)[0]])

    def test_dropped_candidate_does_not_take_repo_slot(self):
        store = DispatchedStore(self.path)
        store.mark("owner/repo#1", "dropped")
        self.assertFalse(store.repo_inflight("owner/repo"))
        store.mark("owner/repo#2", "pr_opened")
        self.assertTrue(store.repo_inflight("owner/repo"))

    def test_deferred_rechecks_obey_utc_deadline(self):
        store = DispatchedStore(self.path)
        for value, blocked in [("2000-01-01T00:00:00Z", False), ("2999-01-01T00:00:00Z", True),
                               ("not-a-date", True), ("2000-01-01T00:00:00", True), (float("nan"), True)]:
            with self.subTest(value=value):
                store.data["key"] = {"status": "deferred", "retry_after": value}
                self.assertEqual(store.is_active("key"), blocked)
        store.data["key"] = {"status": "unrecognized", "retry_after": 1}
        self.assertTrue(store.is_active("key"))

    def test_issue_unknown_blocks_candidate(self):
        c = Candidate("owner/repo", 1, "Crash", "url", is_bug=True, issue_unknown=True)
        self.assertFalse(is_clean(c, DispatchedStore(self.path))[0])

    def test_lock_rejects_overlap_and_releases_on_process_exit(self):
        code = ("from pipeline_state import file_lock; import sys\n"
                "with file_lock(sys.argv[1]):\n"
                " print('locked', flush=True)\n"
                " sys.stdin.readline()\n")
        process = subprocess.Popen([sys.executable, "-S", "-B", "-c", code, str(self.path)],
                                   cwd=str(ROOT / "tools"), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), "locked")
            with self.assertRaises(RuntimeError):
                with file_lock(self.path):
                    self.fail("concurrent writer acquired lock")
            process.stdin.close()
            process.wait(timeout=10)
            self.assertEqual(process.returncode, 0, process.stderr.read())
            with file_lock(self.path):
                atomic_write_json(self.path, {"released": True})
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            for stream in (process.stdin, process.stdout, process.stderr):
                if not stream.closed:
                    stream.close()


if __name__ == "__main__":
    unittest.main()
