"""Offline tests for the self-maintenance tools (review_sweep, maintainer_sweep, revival_scan)."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


review_sweep = load("review_sweep")
maintainer_sweep = load("maintainer_sweep")
revival_scan = load("revival_scan")


class ReviewSweepTests(unittest.TestCase):
    def test_human_activity_filters_bots_and_skips_textualize(self):
        state = {
            "a/b#1": {"state": "OPEN", "updatedAt": "2026-10-24T18:00:00Z"},
            "a/b#2": {"state": "OPEN", "updatedAt": "2026-10-24T18:00:00Z",
                      "query_error": "boom"},
            "Textualize/rich#9": {"state": "OPEN", "updatedAt": "2026-10-24T18:00:00Z"},
            "a/b#3": {"state": "OPEN", "updatedAt": "2026-10-01T18:00:00Z"},
            "a/b#4": {"state": "MERGED", "updatedAt": "2026-10-24T18:00:00Z"},
        }
        calls = []

        def fake_jq(path, jq):
            calls.append(path)
            return "1" if "/issues/1/" in path or "/pulls/1/" in path else "0"

        with patch.object(review_sweep, "STATE", Path("unused.json")), \
             patch.object(review_sweep, "read_json_object", return_value=state), \
             patch.object(review_sweep.sys, "argv", ["x"]), \
             patch.object(review_sweep, "gh_jq", side_effect=fake_jq):
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                review_sweep.main()
        text = out.getvalue()
        self.assertIn("ACTION a/b#1", text)
        self.assertNotIn("a/b#2", text)
        self.assertNotIn("Textualize", text)
        self.assertNotIn("a/b#3", text)
        self.assertNotIn("a/b#4", text)
        # only the live, non-skipped PR was queried, comments + reviews
        self.assertEqual(len(calls), 2)

    def test_rate_limit_output_is_counted_as_zero_not_crash(self):
        state = {"a/b#1": {"state": "OPEN", "updatedAt": "2026-10-24T18:00:00Z"}}
        with patch.object(review_sweep, "STATE", Path("unused.json")), \
             patch.object(review_sweep, "read_json_object", return_value=state), \
             patch.object(review_sweep.sys, "argv", ["x"]), \
             patch.object(review_sweep, "gh_jq", return_value=""):
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                review_sweep.main()
        self.assertIn("0 with human activity", out.getvalue())


class MaintainerSweepTests(unittest.TestCase):
    def test_slice_rotation_partitions_pool(self):
        pool = [f"o/r{i}" for i in range(10)]
        with patch.object(maintainer_sweep, "build_pool", return_value=list(pool)), \
             patch.object(maintainer_sweep, "ThreadPoolExecutor") as ex:
            ex.return_value.__enter__.return_value.map.side_effect = (
                lambda fn, repos: [{"ok": []} for _ in repos])
            import io, contextlib
            for slice_idx, expected in ((0, 4), (1, 3), (2, 3)):
                out = io.StringIO()
                with contextlib.redirect_stdout(out), \
                     patch.object(maintainer_sweep.sys, "argv",
                                  ["x", "--slice", str(slice_idx), "--slices", "3"]):
                    maintainer_sweep.main()
                self.assertIn(f"sweeping {expected} repos (slice {slice_idx}/3",
                              out.getvalue())

    def test_candidates_written_as_json_and_skips_counted(self):
        results = [{"ok": [{"key": "o/r#1", "repo": "o/r", "num": 1,
                            "author_association": "MEMBER", "age_days": 9,
                            "comments": 0, "title": "T", "url": "u"}]},
                   {"skip": "dead/repo"}]
        with patch.object(maintainer_sweep, "build_pool", return_value=["o/r", "dead/repo"]), \
             patch.object(maintainer_sweep, "ThreadPoolExecutor") as ex, \
             patch.object(maintainer_sweep, "atomic_write_json") as save, \
             patch.object(maintainer_sweep.sys, "argv",
                          ["x", "--json", "--show-skips"]):
            ex.return_value.__enter__.return_value.map.return_value = results
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                maintainer_sweep.main()
        text = out.getvalue()
        self.assertIn("SKIP dead/repo", text)
        self.assertIn("1 candidates", text)
        self.assertEqual(save.call_args.args[1]["candidates"][0]["key"], "o/r#1")


class RevivalScanTests(unittest.TestCase):
    def test_stale_claiming_pr_is_flagged_and_closed_ignored(self):
        candidates = {"candidates": [
            {"key": "o/r#5", "repo": "o/r", "num": 5, "title": "T", "url": "u"}]}
        prs = [{"n": 10, "updated": "2026-09-01T00:00:00Z", "state": "open"},
               {"n": 11, "updated": "2026-10-24T00:00:00Z", "state": "open"},
               {"n": 12, "updated": "2026-08-01T00:00:00Z", "state": "closed"}]
        with patch.object(revival_scan, "CANDIDATES", Path("unused.json")), \
             patch.object(revival_scan, "read_json_object", return_value=candidates), \
             patch.object(revival_scan.sys, "argv", ["x", "--json"]), \
             patch.object(revival_scan, "claimant_prs", return_value=prs), \
             patch.object(revival_scan, "atomic_write_json") as save:
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                revival_scan.main()
        text = out.getvalue()
        self.assertIn("REVIVAL o/r#5 <- PR #10 stale", text)
        self.assertNotIn("#11", text)
        self.assertNotIn("#12", text)
        self.assertEqual(save.call_args.args[1]["revival"][0]["pr"], 10)

    def test_missing_candidates_file_prints_guidance(self):
        with patch.object(revival_scan, "CANDIDATES", Path("unused.json")), \
             patch.object(revival_scan, "read_json_object", return_value={}), \
             patch.object(revival_scan.sys, "argv", ["x"]):
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                revival_scan.main()
        self.assertIn("run maintainer_sweep.py --json", out.getvalue())


if __name__ == "__main__":
    unittest.main()
