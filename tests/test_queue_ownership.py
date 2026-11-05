"""External contribution views exclude own repositories without deleting history."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from auto_run import Candidate
import work_queue as queue


class QueueOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.stamp = self.now.isoformat()
        self.own = queue.ACCOUNT.lower() + "/example#1"
        self.external = "example/repo#2"
        signals = {name: {"value": True, "at": self.stamp, "source": "https://example.com/proof"}
                   for name in queue.SIGNALS}
        self.state = {"version": 1, "issues": {}, "prs": {}}
        for key, minutes in ((self.own, 45), (self.external, 5)):
            self.state["issues"][key] = {"stage": "probe", "signals": deepcopy(signals),
                "events": [{"at": self.stamp, "minutes": minutes, "note": "Preparation", "stage": "probe"}]}
        for key, minutes in ((self.own, 20), (self.external, 10)):
            self.state["prs"][key] = {"action": "done", "at": self.stamp,
                "source": "https://example.com/review", "note": "Checked",
                "events": [{"at": self.stamp, "minutes": minutes, "note": "Review", "action": "done"}]}

    def test_refresh_excludes_own_candidates_from_both_sources_and_preserves_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            candidates = [Candidate(queue.ACCOUNT.upper() + "/example", 1, "Bug: crash", "",
                                    is_bug=True, checked_at=self.stamp).__dict__,
                          Candidate("Example/Repo", 2, "Bug: crash", "",
                                    is_bug=True, checked_at=self.stamp).__dict__]
            inputs = {
                root / "work_queue.json": self.state,
                root / "round_candidates.json": candidates,
                root / "tools/fresh_candidates.json": {queue.ACCOUNT.lower() + "/inbox#3": {
                    "repo": queue.ACCOUNT.swapcase() + "/inbox", "number": 3, "title": "Bug: crash", "url": "",
                    "issue_unknown": True, "pr_unknown": True, "cmt_unknown": True}},
            }
            for path, data in inputs.items():
                path.write_text(json.dumps(data), encoding="utf-8")
            original = {path: path.read_bytes() for path in inputs}

            rows = queue.refresh(root)

            self.assertEqual([row["key"] for row in rows], [self.external])
            self.assertTrue(rows[0]["ready"])
            self.assertEqual([row["key"] for row in json.loads(
                (root / "work_queue_view.json").read_text(encoding="utf-8"))["tasks"]], [self.external])
            self.assertEqual({path: path.read_bytes() for path in inputs}, original)

    def test_weekly_excludes_own_effort_from_both_sections_but_keeps_external_data(self):
        # Keys are normalized by the CLI; the filter must also tolerate owner case.
        for section in ("issues", "prs"):
            self.state[section][self.own.upper()] = self.state[section].pop(self.own)
        original = deepcopy(self.state)
        cache = {self.external: {"state": "MERGED", "createdAt": self.stamp, "mergedAt": self.stamp}}

        report = "\n".join(queue.weekly(cache, self.state, self.now))

        self.assertIn("本周已记录实际工时：15 分钟", report)
        self.assertIn("本周合并：1", report)
        self.assertEqual(self.state, original)


if __name__ == "__main__":
    unittest.main()
