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
import auto_run
from pipeline_state import atomic_write_json, file_lock

spec = importlib.util.spec_from_file_location("filter_cands", ROOT / "tools/filter_cands.py")
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

    def test_dispatched_keys_are_case_insensitive_without_read_side_effects(self):
        atomic_write_json(self.path, {"Owner/Repo#1": {"status": "pr_opened"},
                                      "Other/Repo#2": {"status": "dropped"}})
        original = self.path.read_bytes()
        store = DispatchedStore(self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(set(store.data), {"owner/repo#1", "other/repo#2"})
        self.assertTrue(store.is_active("OWNER/REPO#1"))
        self.assertEqual(store.status_of("owner/REPO#1"), "pr_opened")
        self.assertTrue(store.repo_inflight("OWNER/repo"))
        candidate = Candidate("owner/repo", 1, "Crash", "url", is_bug=True)
        self.assertFalse(is_clean(candidate, store)[0])
        store.mark("OWNER/REPO#1", "merged")
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(set(saved), {"owner/repo#1", "other/repo#2"})
        self.assertEqual(saved["owner/repo#1"]["status"], "merged")
        self.assertFalse(store.repo_inflight("Owner/Repo"))

    def test_case_collisions_keep_terminal_and_inflight_records_blocked(self):
        for blocked, other in [("dropped", "needs_repro"), ("merged", "pending"),
                               ("closed", "repro_failed"), ("running", "dropped"),
                               ("pr_opened", "repro_failed"), ("unrecognized", "pending")]:
            for reverse in (False, True):
                with self.subTest(blocked=blocked, other=other, reverse=reverse):
                    entries = [("Owner/Repo#1", {"status": blocked, "ts": 1}),
                               ("owner/repo#1", {"status": other, "ts": 2})]
                    atomic_write_json(self.path, dict(reversed(entries) if reverse else entries))
                    store = DispatchedStore(self.path)
                    self.assertTrue(store.is_active("OWNER/REPO#1"))
                    self.assertEqual(store.status_of("owner/repo#1"), blocked)
                    self.assertEqual(store.repo_inflight("Owner/Repo"), blocked in store.ACTIVE)
                    store.mark("unrelated/repo#2", "pending")
                    self.assertTrue(DispatchedStore(self.path).is_active("Owner/Repo#1"))

    def test_case_collision_keeps_unexpired_deferral(self):
        atomic_write_json(self.path, {
            "Owner/Repo#1": {"status": "deferred", "retry_after": "2999-01-01T00:00:00Z"},
            "owner/repo#1": {"status": "deferred", "retry_after": "2000-01-01T00:00:00Z"},
        })
        self.assertTrue(DispatchedStore(self.path).is_active("owner/repo#1"))

    def test_round_repo_limit_is_case_insensitive(self):
        candidates = [Candidate(repo, number, "Crash", "url", is_bug=True)
                      for repo, number in [("Owner/Repo", 1), ("owner/repo", 2)]]
        with patch.object(auto_run, "load_candidates", return_value=candidates), \
             patch.object(auto_run, "DispatchedStore", return_value=DispatchedStore(self.path)), \
             patch.object(auto_run, "_claimed", return_value=True), \
             patch.object(auto_run, "run") as run, \
             patch.object(sys, "argv", ["auto_run.py", "--dry-run", "--per-repo=1"]):
            auto_run.main()
        self.assertEqual(run.call_count, 1)

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
