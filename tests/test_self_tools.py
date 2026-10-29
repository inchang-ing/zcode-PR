"""Offline tests for the self-maintenance tools (review_sweep, maintainer_sweep, revival_scan, session_claims, monitor_fresh)."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
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
session_claims = load("session_claims")
monitor_fresh = load("monitor_fresh")


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 25, tzinfo=timezone.utc).astimezone(tz)


class OfflineTests(unittest.TestCase):
    def setUp(self):
        for patcher in (
            patch("subprocess.run", side_effect=AssertionError("real subprocess prohibited")),
            patch.object(review_sweep, "datetime", FixedDatetime),
            patch.object(revival_scan, "datetime", FixedDatetime),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)


def response(data, returncode=0):
    return SimpleNamespace(stdout=json.dumps(data), stderr="query failed", returncode=returncode)


class ReviewSweepTests(OfflineTests):
    def test_human_activity_filters_bots_self_and_skips_textualize(self):
        state = {
            "a/b#1": {"state": "OPEN", "updatedAt": "2026-10-24T18:00:00Z"},
            "a/b#2": {"state": "OPEN", "updatedAt": "2026-10-24T18:00:00Z",
                      "query_error": "boom"},
            "Textualize/rich#9": {"state": "OPEN", "updatedAt": "2026-10-24T18:00:00Z"},
            "a/b#3": {"state": "OPEN", "updatedAt": "2026-10-01T18:00:00Z"},
            "a/b#4": {"state": "MERGED", "updatedAt": "2026-10-24T18:00:00Z"},
        }
        calls = []

        def fake_api(cmd, **kwargs):
            calls.append(cmd)
            items = [dict(user={"login": login}, created_at="2026-10-24T18:00:00Z",
                          submitted_at="2026-10-24T18:00:00Z")
                     for login in ("human", "inchang-ing", "automation[bot]", "dashboard")]
            return response([items])

        with patch.object(review_sweep, "STATE", Path("unused.json")), \
             patch.object(review_sweep, "load_pr_state", return_value=state), \
             patch.object(review_sweep.sys, "argv", ["x"]), \
             patch("subprocess.run", side_effect=fake_api):
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                review_sweep.main()
        text = out.getvalue()
        self.assertIn("ACTION a/b#1", text)
        self.assertIn("1 human comments, 1 human reviews", text)
        self.assertNotIn("a/b#2", text)
        self.assertNotIn("Textualize", text)
        self.assertNotIn("a/b#3", text)
        self.assertNotIn("a/b#4", text)
        # only the live, non-skipped PR was queried, comments + reviews
        self.assertEqual(len(calls), 2)

    def test_failed_query_is_unknown_not_zero(self):
        state = {"a/b#1": {"state": "OPEN", "updatedAt": "2026-10-24T18:00:00Z"}}
        with patch.object(review_sweep, "STATE", Path("unused.json")), \
             patch.object(review_sweep, "load_pr_state", return_value=state), \
             patch.object(review_sweep.sys, "argv", ["x"]), \
             patch("subprocess.run", return_value=response([], returncode=1)):
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                status = review_sweep.main()
        self.assertEqual(status, 1)
        self.assertIn("UNKNOWN a/b#1", out.getvalue())

    def test_our_reply_after_human_activity_resolves_without_action(self):
        state = {"a/b#1": {"state": "OPEN", "updatedAt": "2026-10-24T18:00:00Z"}}
        # comments: human at 09:00, our reply at 10:00 (both after --since);
        # reviews: none. Latest human item is us -> resolved, not ACTION.
        comments = [
            dict(user={"login": "human"}, created_at="2026-10-24T13:00:00Z"),
            dict(user={"login": "inchang-ing"}, created_at="2026-10-24T14:00:00Z"),
        ]

        def fake_api(cmd, **kwargs):
            if any("/comments" in c for c in cmd):
                return response([comments])
            return response([[]])

        with patch.object(review_sweep, "STATE", Path("unused.json")), \
             patch.object(review_sweep, "load_pr_state", return_value=state), \
             patch.object(review_sweep.sys, "argv", ["x"]), \
             patch("subprocess.run", side_effect=fake_api):
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                review_sweep.main()
        text = out.getvalue()
        self.assertNotIn("ACTION", text)
        self.assertIn("1 resolved (we replied last)", text)

    def test_human_reply_after_ours_stays_actionable(self):
        state = {"a/b#1": {"state": "OPEN", "updatedAt": "2026-10-24T18:00:00Z"}}
        comments = [
            dict(user={"login": "inchang-ing"}, created_at="2026-10-24T13:00:00Z"),
            dict(user={"login": "human"}, created_at="2026-10-24T14:00:00Z"),
        ]

        def fake_api(cmd, **kwargs):
            if any("/comments" in c for c in cmd):
                return response([comments])
            return response([[]])

        with patch.object(review_sweep, "STATE", Path("unused.json")), \
             patch.object(review_sweep, "load_pr_state", return_value=state), \
             patch.object(review_sweep.sys, "argv", ["x"]), \
             patch("subprocess.run", side_effect=fake_api):
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                review_sweep.main()
        self.assertIn("ACTION a/b#1", out.getvalue())

    def test_approved_review_resolves_without_action(self):
        state = {"a/b#1": {"state": "OPEN", "updatedAt": "2026-10-24T18:00:00Z"}}
        reviews = [dict(user={"login": "maintainer"},
                        submitted_at="2026-10-24T15:00:00Z", state="APPROVED")]

        def fake_api(cmd, **kwargs):
            if any("/reviews" in c for c in cmd):
                return response([reviews])
            return response([[]])

        with patch.object(review_sweep, "STATE", Path("unused.json")), \
             patch.object(review_sweep, "load_pr_state", return_value=state), \
             patch.object(review_sweep.sys, "argv", ["x"]), \
             patch("subprocess.run", side_effect=fake_api):
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                review_sweep.main()
        text = out.getvalue()
        self.assertNotIn("ACTION", text)
        self.assertIn("1 resolved (we replied last)", text)

    def test_changes_requested_review_stays_actionable(self):
        state = {"a/b#1": {"state": "OPEN", "updatedAt": "2026-10-24T18:00:00Z"}}
        reviews = [dict(user={"login": "maintainer"},
                        submitted_at="2026-10-24T15:00:00Z",
                        state="CHANGES_REQUESTED")]

        def fake_api(cmd, **kwargs):
            if any("/reviews" in c for c in cmd):
                return response([reviews])
            return response([[]])

        with patch.object(review_sweep, "STATE", Path("unused.json")), \
             patch.object(review_sweep, "load_pr_state", return_value=state), \
             patch.object(review_sweep.sys, "argv", ["x"]), \
             patch("subprocess.run", side_effect=fake_api):
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                review_sweep.main()
        self.assertIn("ACTION a/b#1", out.getvalue())


class MaintainerSweepTests(OfflineTests):
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


class RevivalScanTests(OfflineTests):
    def test_stale_claiming_pr_is_flagged_and_closed_ignored(self):
        candidates = {"candidates": [
            {"key": "o/r#5", "repo": "o/r", "num": 5, "title": "T", "url": "u"}]}
        prs = [{"n": 10, "repo": "o/r", "updated": "2026-09-01T00:00:00Z", "state": "open"},
               {"n": 11, "repo": "o/r", "updated": "2026-10-24T00:00:00Z", "state": "open"},
               {"n": 12, "repo": "o/r", "updated": "2026-08-01T00:00:00Z", "state": "closed"}]
        with patch.object(revival_scan, "CANDIDATES", Path("unused.json")), \
             patch.object(revival_scan, "read_json_object", return_value=candidates), \
             patch.object(revival_scan.sys, "argv", ["x", "--json"]), \
             patch.object(revival_scan, "claimant_prs", return_value=prs), \
             patch.object(revival_scan, "pr_author_association", return_value="CONTRIBUTOR") as association, \
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
        association.assert_called_once_with("o/r", 10)

    def test_missing_candidates_file_prints_guidance(self):
        with patch.object(revival_scan, "CANDIDATES", Path("unused.json")), \
             patch.object(revival_scan, "read_json_object", return_value={}), \
             patch.object(revival_scan.sys, "argv", ["x"]):
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                revival_scan.main()
        self.assertIn("run maintainer_sweep.py --json", out.getvalue())

    def test_dispositions_are_annotated_and_new_faces_are_not(self):
        results = [{"ok": [
            {"key": "python/mypy#22159", "repo": "python/mypy", "num": 22159,
             "author_association": "COLLABORATOR", "age_days": 19,
             "comments": 0, "title": "T", "url": "u"},
            {"key": "new/repo#7", "repo": "new/repo", "num": 7,
             "author_association": "MEMBER", "age_days": 1,
             "comments": 0, "title": "Fresh", "url": "u"},
        ]}]
        with patch.object(maintainer_sweep, "build_pool", return_value=["a/b"]), \
             patch.object(maintainer_sweep, "ThreadPoolExecutor") as ex, \
             patch.object(maintainer_sweep, "atomic_write_json") as save, \
             patch.object(maintainer_sweep.sys, "argv", ["x", "--json"]):
            ex.return_value.__enter__.return_value.map.return_value = results
            import io, contextlib
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                maintainer_sweep.main()
        text = out.getvalue()
        self.assertIn("python/mypy#22159", text)
        self.assertIn("[DISPOSITIONED", text)
        self.assertIn("stand-down", text)
        self.assertIn("new/repo#7", text)
        self.assertNotIn("new/repo#7 [DISPOSITIONED", text)
        saved = save.call_args.args[1]["candidates"]
        dispositioned = [c for c in saved if c["key"] == "python/mypy#22159"]
        self.assertIn("reason", dispositioned[0]["dispositioned"])


class SessionClaimsTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / "session_claims.json"
        patcher = patch.object(session_claims, "CLAIMS_PATH", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_claim_check_release_lifecycle(self):
        self.assertTrue(session_claims.check("o/r#1"))
        self.assertTrue(session_claims.claim("o/r#1"))
        self.assertFalse(session_claims.check("o/r#1"))
        self.assertFalse(session_claims.claim("o/r#1"))  # busy
        self.assertTrue(session_claims.release("o/r#1"))
        self.assertTrue(session_claims.check("o/r#1"))
        self.assertFalse(session_claims.release("o/r#1"))

    def test_expired_claim_is_pruned_on_check(self):
        now = 1_000_000.0
        self.assertTrue(session_claims.claim("o/r#2", now=now - 49 * 3600))
        self.assertTrue(session_claims.check("o/r#2", now=now))
        self.assertEqual(session_claims.list_claims(now=now), {})

    def test_live_claim_blocks(self):
        now = 1_000_000.0
        self.assertTrue(session_claims.claim("o/r#3", now=now))
        self.assertFalse(session_claims.check("o/r#3", now=now + 3600))
        self.assertEqual(
            list(session_claims.list_claims(now=now + 3600)), ["o/r#3"])


class MonitorFreshPoolTests(unittest.TestCase):
    def test_norm_maps_dead_slugs_and_drops_unresolvable_and_blocked(self):
        from repository_policy import DEAD_OR_RENAMED  # noqa: E402
        self.assertEqual(
            monitor_fresh._norm("aiohttp-libs/aiohttp"), "aio-libs/aiohttp")
        self.assertEqual(monitor_fresh._norm("wnblm/nox"), "wntrblm/nox")
        self.assertEqual(monitor_fresh._norm("pyjwt/jwt"), "jpadilla/pyjwt")
        self.assertIsNone(monitor_fresh._norm("hegel-ai/promptic"))
        self.assertIsNone(monitor_fresh._norm("psf/pycodestyle"))
        self.assertIsNone(monitor_fresh._norm("pallets/blinker"))  # blocked owner
        self.assertIsNone(monitor_fresh._norm("vllm-project/vllm"))  # non-testable
        self.assertEqual(monitor_fresh._norm("FastAPI/FastAPI"), "fastapi/fastapi")

    def test_dead_slugs_are_gone_from_built_tiers(self):
        always, rotating = monitor_fresh.build_tiers()
        pool = set(always) | set(rotating)
        for dead in ("aiohttp-libs/aiohttp", "hegel-ai/promptic",
                     "portkey-ai/portkey-python", "wnblm/nox",
                     "pytest-dev/pytest-lazy-fixture", "psf/pycodestyle",
                     "pallets/blinker"):
            self.assertNotIn(dead, pool)
        self.assertIn("aio-libs/aiohttp", pool)
        self.assertIn("wntrblm/nox", pool)

    def test_always_slice_rotation_covers_everything(self):
        always, rotating = monitor_fresh.build_tiers()
        slices = [set(always[i::monitor_fresh.ALWAYS_SLICES])
                  for i in range(monitor_fresh.ALWAYS_SLICES)]
        covered = slices[0] | slices[1]
        self.assertEqual(covered, set(always))
        self.assertEqual(len(slices[0]), len(slices[1]))  # even split


if __name__ == "__main__":
    unittest.main()
