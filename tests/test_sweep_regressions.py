"""Exercise pagination and failure handling through the real sweep entry points."""
import contextlib
import io
import json
import runpy
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from test_self_tools import OfflineTests, response, review_sweep, revival_scan


SINCE = "2026-10-24T12:00:00Z"


def timeline_pr(repo="other/project", number=10):
    return {"event": "cross-referenced", "source": {"issue": {
        "number": number, "state": "open", "updated_at": "2026-09-01T00:00:00Z",
        "user": {"login": "maintainer"},
        "pull_request": {"url": f"https://api.github.com/repos/{repo}/pulls/{number}"}}}}


class ReviewPaginationTests(OfflineTests):
    def test_offset_since_compares_instants_and_uses_utc_api_parameter(self):
        since = '2026-10-24T20:00:00+08:00'
        state = {'a/b#1': {'state': 'OPEN', 'updatedAt': '2026-10-24T13:00:00Z'}}
        item = {'user': {'login': 'human'}, 'created_at': '2026-10-24T13:00:00Z',
                'submitted_at': '2026-10-24T13:00:00Z'}
        with patch.object(review_sweep, 'load_pr_state', return_value=state), \
             patch.object(review_sweep.sys, 'argv', ['x', '--since', since]), \
             patch('subprocess.run', return_value=response([[item]])) as run, \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(review_sweep.main(), 0)
        self.assertIn('ACTION a/b#1: 1 human comments, 1 human reviews', out.getvalue())
        self.assertEqual(run.call_count, 2)
        # The comments endpoint fetches the full list (latest-human tracking);
        # the UTC-instant since comparison happens client-side in the sweep.
        comments_url = run.call_args_list[0].args[0][2]
        self.assertIn('/comments', comments_url)
        self.assertNotIn('since=', comments_url)

    def test_fractional_seconds_and_activity_offsets_respect_since_boundary(self):
        stamps = ['2026-10-24T12:00:00Z', '2026-10-24T20:00:00.500+08:00',
                  '2026-10-24T12:00:00.501Z']
        items = [{'user': {'login': 'human'}, 'created_at': stamp, 'submitted_at': stamp}
                 for stamp in stamps]
        for kind in ('comments', 'reviews'):
            with self.subTest(kind=kind), patch('subprocess.run', return_value=response([items])):
                count, latest = review_sweep.human_activity(
                    'a/b', '1', kind,
                    review_sweep.parse_timestamp('2026-10-24T12:00:00.500Z'))
                self.assertEqual(count, 2)
                self.assertEqual(latest[0], 'human')

    def test_invalid_since_is_cli_error_before_state_or_api_reads(self):
        for since in ('not-a-date', '2026-10-24T12:00:00', '2026-99-99T99:99:99Z',
                      '0001-01-01T00:00:00+01:00', ''):
            with self.subTest(since=since):
                with patch.object(review_sweep.sys, 'argv', ['x', '--since', since]), \
                     patch.object(review_sweep, 'load_pr_state', return_value={}) as read, \
                     patch('subprocess.run') as run, contextlib.redirect_stderr(io.StringIO()), \
                     contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
                    review_sweep.main()
                self.assertEqual(result.exception.code, 2)
                read.assert_not_called()
                run.assert_not_called()

    def test_invalid_pr_update_is_unknown_without_hiding_other_pr(self):
        item = {'user': {'login': 'human'}, 'created_at': SINCE, 'submitted_at': SINCE}
        for stamp in (None, '', 'not-a-date', '2026-10-24T12:00:00', '2026-99-99T99:99:99Z'):
            state = {'a/b#1': {'state': 'OPEN', 'updatedAt': stamp},
                     'a/b#2': {'state': 'OPEN', 'updatedAt': SINCE}}
            with self.subTest(stamp=stamp), \
                 patch.object(review_sweep, 'load_pr_state', return_value=state), \
                 patch.object(review_sweep.sys, 'argv', ['x', '--since', SINCE]), \
                 patch('subprocess.run', return_value=response([[item]])) as run, \
                 contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(review_sweep.main(), 1)
                self.assertIn('UNKNOWN a/b#1', out.getvalue())
                self.assertIn('ACTION a/b#2', out.getvalue())
                self.assertEqual(run.call_count, 2)

    def test_invalid_activity_time_is_unknown_without_hiding_other_pr(self):
        state = {f'a/b#{n}': {'state': 'OPEN', 'updatedAt': SINCE} for n in (1, 2)}
        for kind in ('comments', 'reviews'):
            for stamp in ('not-a-date', '2026-10-24T12:00:00', '2026-99-99T99:99:99Z'):
                def fake_api(cmd, **kwargs):
                    item = {'user': {'login': 'human'}, 'created_at': SINCE, 'submitted_at': SINCE}
                    if '/1/' in cmd[2] and ('/reviews?' in cmd[2]) == (kind == 'reviews'):
                        item['created_at' if kind == 'comments' else 'submitted_at'] = stamp
                    return response([[item]])
                with self.subTest(kind=kind, stamp=stamp), \
                     patch.object(review_sweep, 'load_pr_state', return_value=state), \
                     patch.object(review_sweep.sys, 'argv', ['x', '--since', SINCE]), \
                     patch('subprocess.run', side_effect=fake_api) as run, \
                     contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(review_sweep.main(), 1)
                    self.assertIn('UNKNOWN a/b#1', out.getvalue())
                    self.assertIn('ACTION a/b#2', out.getvalue())
                    self.assertEqual(run.call_count, 3 if kind == 'comments' else 4)

    def test_cli_exit_codes_distinguish_empty_success_from_query_failure(self):
        cases = [(review_sweep, ["--since", SINCE],
                  {"a/b#1": {"state": "OPEN", "updatedAt": SINCE}}),
                 (revival_scan, [], {"candidates": [{"key": "a/b#1", "repo": "a/b", "num": 1}]})]
        for module, args, data in cases:
            for failed in (False, True):
                with self.subTest(module=module.__name__, failed=failed), \
                     patch("pr_state.load_pr_state" if module is review_sweep else "pipeline_state.read_json_object", return_value=data if failed else {}), \
                     patch.object(module.sys, "argv", [module.__file__, *args]), \
                     patch("subprocess.run", return_value=response([], 1)), \
                     contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
                    runpy.run_path(module.__file__, run_name="__main__")
                self.assertEqual(result.exception.code, 1 if failed else 0)

    def test_later_pages_include_human_feedback_and_filter_old_and_pending(self):
        early = [{"user": {"login": "robot[bot]"}, "created_at": SINCE,
                  "submitted_at": SINCE}] * 100
        late = [{"user": {"login": "human"}, "created_at": SINCE, "submitted_at": SINCE},
                {"user": {"login": "inchang-ing"}, "created_at": SINCE, "submitted_at": SINCE},
                {"user": {"login": "old"}, "created_at": "2026-01-01T00:00:00Z",
                 "submitted_at": "2026-01-01T00:00:00Z"}]
        for kind in ("comments", "reviews"):
            pages = [early, late + ([{"submitted_at": None, "state": "PENDING"}] if kind == "reviews" else [])]
            with self.subTest(kind=kind), patch("subprocess.run", return_value=response(pages)) as run:
                count, latest = review_sweep.human_activity(
                    "a/b", "1", kind, review_sweep.parse_timestamp(SINCE))
                self.assertEqual(count, 1)
                # The bot page-1 items are skipped, so the newest non-bot item
                # is the human comment, not our own same-timestamp reply.
                self.assertEqual(latest[0], "human")
                cmd = run.call_args.args[0]
                self.assertIn("--paginate", cmd)
                self.assertIn("--slurp", cmd)
                self.assertIn("per_page=100", " ".join(cmd))

    def test_failures_do_not_turn_into_empty_activity(self):
        bad = [response([[{"user": {"login": "human"}, "created_at": SINCE}]], 1),
               response({}), response([[1]]), response([[{"created_at": SINCE}]]),
               response([[{"user": {"login": "human"}}]])]
        bad.append(SimpleNamespace(returncode=0, stdout="not JSON"))
        for result in bad:
            with self.subTest(result=result), patch("subprocess.run", return_value=result):
                with self.assertRaises(ValueError):
                    review_sweep.human_activity(
                        "a/b", "1", "comments", review_sweep.parse_timestamp(SINCE))
        for exc in (OSError("missing"), UnicodeError("invalid encoding"), subprocess.TimeoutExpired("gh", 60)):
            with self.subTest(error=exc), patch("subprocess.run", side_effect=exc):
                with self.assertRaises(ValueError):
                    review_sweep.human_activity(
                        "a/b", "1", "comments", review_sweep.parse_timestamp(SINCE))

    def test_unknown_pr_does_not_hide_later_actionable_pr(self):
        state = {f"a/b#{n}": {"state": "OPEN", "updatedAt": SINCE} for n in (1, 2)}

        def fake_api(cmd, **kwargs):
            if "/1/" in " ".join(cmd):
                return response([], 1)
            return response([[{"user": {"login": "human"}, "created_at": SINCE,
                               "submitted_at": SINCE}]])

        out = io.StringIO()
        with patch.object(review_sweep, "load_pr_state", return_value=state), \
             patch.object(review_sweep.sys, "argv", ["x", "--since", SINCE]), \
             patch("subprocess.run", side_effect=fake_api), contextlib.redirect_stdout(out):
            self.assertEqual(review_sweep.main(), 1)
        self.assertIn("UNKNOWN a/b#1", out.getvalue())
        self.assertIn("ACTION a/b#2", out.getvalue())

    def test_successful_empty_activity_is_not_unknown(self):
        state = {"a/b#1": {"state": "OPEN", "updatedAt": SINCE}}
        with patch.object(review_sweep, "load_pr_state", return_value=state), \
             patch.object(review_sweep.sys, "argv", ["x", "--since", SINCE]), \
             patch("subprocess.run", return_value=response([[]])), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(review_sweep.main(), 0)
        self.assertIn("0 with human activity, 0 resolved (we replied last), 0 unknown",
                      out.getvalue())


class RevivalPaginationTests(OfflineTests):
    def test_timeline_pages_preserve_cross_repository_identity(self):
        pages = [[{"event": "commented"}, {"event": "cross-referenced", "source": {
            "issue": {"number": 1}}}], [timeline_pr()]]
        with patch("subprocess.run", return_value=response(pages)) as run:
            prs = revival_scan.claimant_prs("a/b", 5)
        self.assertEqual(len(prs), 1)
        self.assertEqual(prs[0]["repo"], "other/project")
        self.assertEqual(prs[0]["n"], 10)
        self.assertEqual(prs[0]["url"], "https://github.com/other/project/pull/10")
        self.assertIn("--slurp", run.call_args.args[0])

    def test_bad_timeline_and_untrusted_pr_urls_are_unknown(self):
        bad = [response([], 1), response({}), response([[1]]), response([[{}]]),
               response([[{"event": "cross-referenced"}]])]
        for url in ("https://evil.example/repos/other/project/pulls/10",
                    "https://api.github.com@evil.example/repos/other/project/pulls/10",
                    "https://api.github.com/repos/other/project/pulls/10?x=1",
                    "https://api.github.com/repos/other/project/pulls/11", None, 123):
            event = timeline_pr()
            event["source"]["issue"]["pull_request"]["url"] = url
            bad.append(response([[event]]))
        for key, value in (("state", "unknown"), ("updated_at", None), ("user", [1]),
                           ("pull_request", {})):
            event = timeline_pr()
            event["source"]["issue"][key] = value
            bad.append(response([[event]]))
        for result in bad:
            with self.subTest(result=result), patch("subprocess.run", return_value=result):
                with self.assertRaises(ValueError):
                    revival_scan.claimant_prs("a/b", 5)
        for exc in (OSError("missing"), UnicodeError("invalid encoding"), subprocess.TimeoutExpired("gh", 60)):
            with self.subTest(error=exc), patch("subprocess.run", side_effect=exc):
                with self.assertRaises(ValueError):
                    revival_scan.claimant_prs("a/b", 5)

    def test_cross_repo_author_lookup_and_unknowns_are_not_revival_candidates(self):
        candidates = [{"key": f"a/b#{n}", "repo": "a/b", "num": n,
                       "title": "bug", "url": f"https://github.com/a/b/issues/{n}"}
                      for n in (1, 2, 3, 4)]
        calls = []

        def fake_api(cmd, **kwargs):
            path = cmd[2]
            calls.append(path)
            if "/issues/1/" in path:
                return response([], 1)
            if "/timeline" in path:
                number = int(path.split("/issues/")[1].split("/")[0])
                return response([[timeline_pr(number=number)]])
            if path == "repos/other/project/pulls/2":
                return SimpleNamespace(returncode=1, stdout="NONE")
            return SimpleNamespace(returncode=0, stdout="MEMBER")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates_file = root / "candidates.json"
            candidates_file.write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
            out = io.StringIO()
            with patch.object(revival_scan, "ROOT", root), \
                 patch.object(revival_scan, "CANDIDATES", candidates_file), \
                 patch.object(revival_scan.sys, "argv", ["x", "--json"]), \
                 patch("subprocess.run", side_effect=fake_api), contextlib.redirect_stdout(out):
                self.assertEqual(revival_scan.main(), 1)
            saved = json.loads((root / "work/ledger/revival_candidates.json").read_text())
        self.assertEqual([x["issue"] for x in saved["revival"]], ["a/b#3", "a/b#4"])
        self.assertEqual(len(saved["unknown"]), 2)
        self.assertTrue(all(x["maintainer_owned"] for x in saved["revival"]))
        self.assertEqual(saved["revival"][0]["pr_repo"], "other/project")
        self.assertIn("repos/other/project/pulls/2", calls)
        self.assertNotIn("repos/a/b/pulls/2", calls)
        self.assertIn("UNKNOWN a/b#2", out.getvalue())
        self.assertIn("other/project#3", out.getvalue())

    def test_association_lookup_errors_are_explicit(self):
        for result in (SimpleNamespace(returncode=1, stdout="OWNER"),
                       SimpleNamespace(returncode=0, stdout=""),
                       SimpleNamespace(returncode=0, stdout="unexpected")):
            with self.subTest(result=result), patch("subprocess.run", return_value=result):
                with self.assertRaises(ValueError):
                    revival_scan.pr_author_association("a/b", 1)
        for exc in (OSError("missing"), UnicodeError("invalid encoding"), subprocess.TimeoutExpired("gh", 60)):
            with self.subTest(error=exc), patch("subprocess.run", side_effect=exc):
                with self.assertRaises(ValueError):
                    revival_scan.pr_author_association("a/b", 1)

    def test_valid_association_and_empty_timeline(self):
        for association in ("MEMBER", "NONE"):
            result = SimpleNamespace(returncode=0, stdout=association)
            with patch("subprocess.run", return_value=result):
                self.assertEqual(revival_scan.pr_author_association("a/b", 1), association)
        with patch("subprocess.run", return_value=response([[]])):
            self.assertEqual(revival_scan.claimant_prs("a/b", 1), [])

    def test_invalid_date_is_unknown_and_does_not_request_author(self):
        candidate = {"key": "a/b#1", "repo": "a/b", "num": 1, "title": "bug"}
        for date in ("not a date", "2026-01-01T00:00:00"):
            event = timeline_pr()
            event["source"]["issue"]["updated_at"] = date
            with patch.object(revival_scan, "read_json_object", return_value={"candidates": [candidate]}), \
                 patch.object(revival_scan.sys, "argv", ["x"]), \
                 patch("subprocess.run", return_value=response([[event]])) as run, \
                 contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(revival_scan.main(), 1)
                self.assertIn("UNKNOWN a/b#1", out.getvalue())
                self.assertEqual(run.call_count, 1)
