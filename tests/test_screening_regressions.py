"""Offline examples that must not become clean candidates or healthy CI."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from auto_run import Candidate, DispatchedStore, is_clean
import monitor_round
import monitor_oss
import filter_cands
import vet
from repository_policy import policy_reason


ISSUE = dict(number=1, title="Bug: crash", state="OPEN", labels=[{"name": "bug"}],
             assignees=[], body="Reproducible crash")
CLAIMS = ["I can open a PR", "I have a patch", "I will add tests", "/assign",
          "Codex is assisting", "not ready for a PR", "not yet ready for PR",
          "I would like to implement this", "I’ll submit a PR", "Happy to send a PR",
          "I'm working on a fix", "I started working on this issue", "I'm working on it",
          "I would be glad to fix this", "I would be happy to submit a PR",
          "Happy to help implement a fix", "I started working on a patch", "Happy to work on the fix"]
CLAIMS += [f"I'm working on {article} {target}" for article in ("a", "the")
           for target in ("fix", "patch", "PR", "pull request")]


class ScreeningRegressions(unittest.TestCase):
    def setUp(self):
        tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.store = DispatchedStore(str(Path(tmp) / "state.json"))
        self.enterContext(patch.object(vet, 'live_capacity', return_value={'allowed': True}))
        self.enterContext(patch.object(vet, 'DispatchedStore', return_value=self.store))
        self.enterContext(redirect_stdout(io.StringIO()))
        self.enterContext(patch.object(monitor_round.time, "sleep"))

    def candidate(self, repo="example/project", **kwargs):
        return Candidate(repo, 1, "Bug: crash", "", is_bug=True, **kwargs)

    def live(self, repo, issue):
        with patch.object(vet, "gh", side_effect=[json.dumps(issue), "[[]]", "[[]]"]):
            return vet.vet(self.candidate(repo))[0]

    def test_claims_block_in_body_and_comments_in_both_entry_points(self):
        for phrase in CLAIMS:
            for in_body in (True, False):
                with self.subTest(phrase=phrase, in_body=in_body):
                    issue = {**ISSUE, "body": phrase if in_body else ISSUE["body"]}
                    comments = [] if in_body else [phrase]
                    with patch.object(vet, "gh", side_effect=[json.dumps(issue), "[[]]",
                            json.dumps([[], [{"body": c} for c in comments]])]):
                        self.assertEqual(vet.vet(self.candidate())[0], "DROP")
                    with patch.object(monitor_round, "get_issues", return_value=[issue]), \
                         patch.object(monitor_round, "has_linked_pr", return_value=False), \
                         patch.object(monitor_round, "get_comments", return_value=comments), \
                         patch.object(monitor_round, "atomic_write_json") as save:
                        monitor_round.scan(["example/project"], "unused.json")
                    self.assertEqual(save.call_args.args[1], [])

    def test_ordinary_text_stays_clean(self):
        for body in ["Please add tests", "I cannot open a PR", "I do not have a patch",
                     "See https://example.org/assign for documentation", "Crash in assignment"]:
            with self.subTest(body=body):
                self.assertEqual(self.live("example/project", {**ISSUE, "body": body}), "CLEAN")

    def test_environment_and_log_offers_stay_clean_in_body_and_comments(self):
        for phrase in ("I'm working on Windows 11 and the parser crashes.",
                       "Happy to work on Windows; the parser still crashes.",
                       "I'm working on a project that uses this library.",
                       "I started working with this library last week.",
                       "I would be happy to provide logs if needed.",
                       "I would be happy to submit logs.", "Happy to help collect logs."):
            for in_body in (True, False):
                with self.subTest(phrase=phrase, in_body=in_body):
                    issue = {**ISSUE, "body": phrase if in_body else ISSUE["body"]}
                    comments = [] if in_body else [phrase]
                    with patch.object(vet, "gh", side_effect=[json.dumps(issue), "[[]]",
                            json.dumps([[{"body": c} for c in comments]])]):
                        self.assertEqual(vet.vet(self.candidate())[0], "CLEAN")
                    with patch.object(monitor_round, "get_issues", return_value=[issue]), \
                         patch.object(monitor_round, "has_linked_pr", return_value=False), \
                         patch.object(monitor_round, "get_comments", return_value=comments), \
                         patch.object(monitor_round, "atomic_write_json") as save:
                        monitor_round.scan(["example/project"], "unused.json")
                    self.assertEqual(len(save.call_args.args[1]), 1)

    def test_manual_exclusions_apply_to_every_repository_case(self):
        for repo, number in (("optuna/optuna", 6898), ("crewAIInc/crewAI", 8111)):
            for spelling in (repo, repo.lower(), repo.upper()):
                with self.subTest(repo=spelling):
                    candidate = Candidate(spelling, number, "Bug: crash", "", is_bug=True)
                    self.assertFalse(is_clean(candidate, self.store)[0])
                    self.assertEqual(filter_cands.fresh_candidates([candidate], self.store), [])
        self.assertTrue(is_clean(Candidate("OPTUNA/OPTUNA", 6899, "Bug: crash", "", is_bug=True),
                                 self.store)[0])

    def test_repository_policy_blocks_local_and_live_checks(self):
        for repo in ["stanfordnlp/dspy", "StanfordNLP/DSPy", "mem0ai/mem0",
                     "langchain-ai/langchain", "langchain-ai/langgraph",
                     "pallets/werkzeug", "matplotlib/matplotlib", "UKGovernmentBEIS/inspect_ai"]:
            with self.subTest(repo=repo):
                self.assertFalse(is_clean(self.candidate(repo), self.store)[0])
                self.assertEqual(self.live(repo, ISSUE), "DROP")

    def test_textualize_owner_is_handoff_only_after_verified_block(self):
        # 2026-10-24: API CreatePullRequest FORBIDDEN and the web compare form does
        # not render for this account, even after 2FA; external accounts opened fork
        # PRs the same month. Fix flow is fork-branch + issue comment with a compare
        # link for a maintainer — never a retry of PR creation.
        from repository_policy import POLICY_EVIDENCE
        self.assertEqual(policy_reason("Textualize/rich"), "受限/禁投仓库: textualize/rich")
        self.assertEqual(policy_reason("Textualize/textual"), "受限/禁投仓库: textualize/textual")
        self.assertEqual(POLICY_EVIDENCE["textualize"]["scope"], "owner")
        self.assertIn("handoff-only", POLICY_EVIDENCE["textualize"]["review"])

    def test_recorded_submission_bans_block_scan_filter_and_live_vet(self):
        for repo in ("pypa/packaging", "PyPA/Packaging", "google/jax", "jax-ml/jax",
                     "modelcontextprotocol/servers", "ModelContextProtocol/Servers"):
            with self.subTest(repo=repo), \
                 patch.object(monitor_round, "get_issues", return_value=[ISSUE]), \
                 patch.object(monitor_round, "has_linked_pr", return_value=False), \
                 patch.object(monitor_round, "get_comments", return_value=[]), \
                 patch.object(monitor_round, "atomic_write_json") as save:
                monitor_round.scan([repo], Path(self.store.path).with_name("candidates.json"))
                self.assertEqual(save.call_args.args[1], [])
                self.assertEqual(filter_cands.fresh_candidates([self.candidate(repo)], self.store), [])
                self.assertEqual(self.live(repo, ISSUE), "DROP")

    def test_assigned_python_sdk_still_requires_manual_participation(self):
        self.assertIn("handoff-only", policy_reason("modelcontextprotocol/servers"))
        self.assertIn("人工门禁", policy_reason("modelcontextprotocol/python-sdk", [], ["inchang-ing"]))

    def test_focused_pool_exclusions_do_not_become_global_or_owner_bans(self):
        cases = [("pypa/build", [], []), ("google/python-fire", [], []),
                 ("networkx/networkx", [], []), ("pydantic/pydantic", [], []),
                 ("mem0ai/mem0", ["accepted"], []),
                 ("langchain-ai/langgraph", [], ["inchang-ing"])]
        for repo, labels, assignees in cases:
            with self.subTest(repo=repo):
                self.assertEqual(policy_reason(repo, labels, assignees), "")

    def test_label_gate_accepts_eligible_issue_and_rechecks_live_labels(self):
        repo = "mem0ai/mem0"
        self.assertTrue(is_clean(self.candidate(repo, labels=["bug", "Accepted"]), self.store)[0])
        self.assertEqual(self.live(repo, {**ISSUE, "labels": [{"name": "accepted"}]}), "CLEAN")
        self.assertEqual(self.live(repo, ISSUE), "DROP")

    def test_vet_rechecks_bug_eligibility_from_live_title_and_labels(self):
        cases = [
            ("Bug: crash", ["enhancement"], "DROP"),
            ("Add a new option", [], "DROP"),
            ("Regression after upgrade", [], "CLEAN"),
            ("Unexpected result", ["type: bug"], "CLEAN"),
            ("Add a new option", ["bug", "enhancement"], "CLEAN"),
            ("Bug: crash", ["needs triage"], "WARN"),
            ("Bug: crash", ["bug", "needs discussion"], "WARN"),
        ]
        for title, labels, expected in cases:
            with self.subTest(title=title, labels=labels):
                issue = {**ISSUE, "title": title,
                         "labels": [{"name": label} for label in labels]}
                self.assertEqual(self.live("example/project", issue), expected)

    def test_vet_malformed_live_title_is_unknown(self):
        for title in (None, 1, [], "", "   "):
            with self.subTest(title=title):
                self.assertEqual(self.live("example/project", {**ISSUE, "title": title}), "UNKNOWN")
        issue = {key: value for key, value in ISSUE.items() if key != "title"}
        self.assertEqual(self.live("example/project", issue), "UNKNOWN")

    def test_vet_cli_drops_candidate_reclassified_after_snapshot(self):
        candidate_path = Path(self.store.path).with_name("candidates.json")
        candidate_path.write_text(json.dumps([{
            "repo": "example/project", "number": 1, "title": "Bug: crash", "url": "",
            "is_bug": True, "labels": ["bug"],
        }]), encoding="utf-8")
        live_issue = {**ISSUE, "labels": [{"name": "enhancement"}]}
        output = io.StringIO()
        with patch.object(vet, "DispatchedStore", return_value=self.store), \
             patch.object(vet, "gh", side_effect=[json.dumps(live_issue), "[[]]", "[[]]"]), \
             redirect_stdout(output):
            self.assertEqual(vet.main(["--candidates", str(candidate_path)]), 0)
        self.assertIn("DROP=1", output.getvalue())
        self.assertNotIn("CLEAN_CAND|", output.getvalue())

    def test_assignment_requires_self_and_rejects_other_assignees(self):
        for names, allowed in [([], False), (["inchang-ing"], True), (["someone"], False),
                               (["inchang-ing", "someone"], False)]:
            with self.subTest(names=names):
                c = self.candidate("langchain-ai/langchain", assignees=names)
                self.assertEqual(is_clean(c, self.store)[0], allowed)
                issue = {**ISSUE, "assignees": [{"login": n} for n in names]}
                self.assertEqual(self.live(c.repo, issue), "CLEAN" if allowed else "DROP")

    def test_scanner_keeps_self_assignment_for_policy_and_snapshot(self):
        issue = {**ISSUE, "assignees": [{"login": "inchang-ing"}]}
        with patch.object(monitor_round, "get_issues", return_value=[issue]), \
             patch.object(monitor_round, "has_linked_pr", return_value=False), \
             patch.object(monitor_round, "get_comments", return_value=[]), \
             patch.object(monitor_round, "atomic_write_json") as save:
            monitor_round.scan(["langchain-ai/langchain"], "unused.json")
        saved = save.call_args.args[1]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["assignees"], ["inchang-ing"])
        self.assertTrue(is_clean(Candidate(**saved[0]), self.store)[0])

    def test_scanner_applies_repository_gate(self):
        for repo in ("stanfordnlp/dspy", "mem0ai/mem0", "langchain-ai/langchain"):
            with self.subTest(repo=repo), \
                 patch.object(monitor_round, "get_issues", return_value=[ISSUE]), \
                 patch.object(monitor_round, "has_linked_pr", return_value=False), \
                 patch.object(monitor_round, "get_comments", return_value=[]), \
                 patch.object(monitor_round, "atomic_write_json") as save:
                monitor_round.scan([repo], "unused.json")
                self.assertEqual(save.call_args.args[1], [])

    def test_existing_gates_and_malformed_assignment_remain_conservative(self):
        for repo in ("apache/arrow", "vllm-project/vllm", "huggingface/peft",
                     "pydantic/pydantic-ai", "mlflow/mlflow", "camel-ai/camel",
                     "HypothesisWorks/hypothesis", "useblocks/sphinx-needs",
                     "pre-commit/pre-commit", "python-jsonschema/jsonschema", "Textualize/textual"):
            with self.subTest(repo=repo):
                self.assertTrue(policy_reason(repo))
        self.assertFalse(policy_reason("mlflow/mlflow", ["ready"]))
        self.assertFalse(policy_reason("UKGovernmentBEIS/inspect_ai", ["accepted"]))
        self.assertIn("人工门禁", policy_reason("huggingface/peft", [], ["inchang-ing"]))
        for assignees in (None, [None], [""]):
            self.assertTrue(policy_reason("example/project", [], assignees))
        for assignees in ([{}], [{"login": None}], [None]):
            self.assertEqual(self.live("example/project", {**ISSUE, "assignees": assignees}), "UNKNOWN")


class CIRegressions(unittest.TestCase):
    def test_known_success_pending_and_neutral_do_not_alert(self):
        for roll in ([], [{"state": "SUCCESS"}], [{"state": "PENDING"}],
                     [{"status": "COMPLETED", "conclusion": "NEUTRAL"}],
                     [{"status": "REQUESTED"}]):
            self.assertFalse(monitor_oss.ci_failed(monitor_oss.ci_summary(roll)))

    def test_failure_and_action_required_alert(self):
        for check in [{"state": "FAILURE"}, {"state": "ERROR"},
                      {"status": "COMPLETED", "conclusion": "ACTION_REQUIRED"},
                      {"status": "COMPLETED", "conclusion": "STARTUP_FAILURE"}]:
            with self.subTest(check=check):
                self.assertTrue(monitor_oss.ci_failed(monitor_oss.ci_summary([check])))

    def test_mixed_checks_count_every_result_and_preserve_unknown(self):
        summary = monitor_oss.ci_summary([
            {"state": "SUCCESS"}, {"state": "PENDING"},
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "WAITING"}, {"status": "COMPLETED", "conclusion": "SKIPPED"},
            {"status": "COMPLETED", "conclusion": "NEW_STATE"}])
        self.assertIn("2✓/0✗/2…/0ERR", summary)
        self.assertIn("1SKIP", summary)
        self.assertIn("1UNKNOWN", summary)
        self.assertTrue(monitor_oss.ci_failed(summary))

    def test_empty_and_malformed_rollups_are_distinct(self):
        self.assertEqual(monitor_oss.ci_summary([]), "no-checks")
        for roll in (None, {}, [None], [{}]):
            with self.subTest(roll=roll):
                self.assertIn("UNKNOWN", monitor_oss.ci_summary(roll))
                self.assertTrue(monitor_oss.ci_failed(monitor_oss.ci_summary(roll)))


if __name__ == "__main__":
    unittest.main()
