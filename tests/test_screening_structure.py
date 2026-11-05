"""Offline regressions for shared screening rules and declarative repository pools."""
import ast
import contextlib
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import claim_check
import scan_docs
import repository_policy as policy


class SharedClaimTests(unittest.TestCase):
    def check(self, pages):
        result = subprocess.CompletedProcess([], 0, json.dumps(pages), "")
        output = io.StringIO()
        with patch.object(claim_check.github_read.subprocess, "run", return_value=result) as run, \
             patch.object(sys, "argv", ["claim_check.py", "example/repo#1"]), \
             contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as end:
            claim_check.main()
        return end.exception.code, output.getvalue(), run.call_args.args[0]

    def comment(self, body, user="contributor"):
        return {"user": {"login": user}, "created_at": "2026-11-05T01:00:00Z", "body": body}

    def test_claim_check_uses_shared_rule_on_later_page(self):
        for body in ("I can open a PR", "I have a patch", "not ready for a PR", "I have a PR",
                     "Patch is ready", "branch ready", "Waiting for assignment", "Please assign me",
                     "I can work on this", "I will do this", "I'd like to pick this", "Assigned to me"):
            with self.subTest(body=body):
                code, output, args = self.check([[self.comment("Confirmed")] * 100,
                                                [self.comment(body)]])
                self.assertEqual(code, 1)
                self.assertIn("CLAIMED", output)
                self.assertIn("--paginate", args)
                self.assertIn("--slurp", args)

    def test_comments_with_environment_context_are_clear(self):
        for body in ("I'm working on Windows 11 and it crashes.", "Happy to work on Windows."):
            with self.subTest(body=body):
                code, output, _ = self.check([[self.comment(body)]])
                self.assertEqual(code, 0)
                self.assertIn("CLEAR", output)
                self.assertTrue(scan_docs.interesting({"body": body, "labels": []})[0])

    def test_docs_uses_shared_claims(self):
        for body in ("I can open a PR", "not ready for a PR", "I have a patch"):
            with self.subTest(body=body):
                self.assertFalse(scan_docs.interesting({"body": body, "labels": []})[0])

    def test_malformed_comments_are_unknown(self):
        for payload in ([], {}, [[] , [None]], [[{}]], [[self.comment(None)]]):
            with self.subTest(payload=payload):
                code, output, _ = self.check(payload)
                self.assertEqual(code, 1)
                self.assertIn("UNKNOWN", output)

    def test_transport_failure_is_unknown(self):
        for failure in (FileNotFoundError("gh"), subprocess.TimeoutExpired("gh", 90)):
            with self.subTest(failure=failure), \
                 patch.object(claim_check.github_read.subprocess, "run", side_effect=failure):
                comments, error = claim_check.comments("example/repo", 1)
                self.assertIsNone(comments)
                self.assertTrue(error)


class PolicyStructureTests(unittest.TestCase):
    def test_mypy_only_allows_docs(self):
        self.assertTrue(policy.policy_reason("python/mypy"))
        for kind in ("bug", "small_fix", "tooling", "unknown"):
            self.assertTrue(policy.policy_reason("Python/Mypy", kind=kind))
        self.assertEqual(policy.policy_reason("python/mypy", kind="docs"), "")
        self.assertTrue(policy.policy_reason("python/mypy", assignees=["other"], kind="docs"))

    def test_one_record_preserves_both_python_sdk_observations(self):
        record = policy.REPOSITORY_POLICIES["modelcontextprotocol/python-sdk"]
        self.assertEqual({e["observed_at"] for e in record["evidence"]},
                         {"2026-10-18", "2026-11-03"})
        self.assertTrue(record["reason"])
        self.assertEqual(policy.REPOSITORY_POLICIES["python/mypy"]["allowed_kinds"], ("docs",))
        for registry in (policy.REPOSITORY_POLICIES, policy.OWNER_POLICIES):
            self.assertTrue(all(key == key.lower() for key in registry))
            self.assertTrue(all(record["reason"] and record["evidence"] for record in registry.values()))

    def test_policy_literal_keys_are_unique(self):
        tree = ast.parse(Path(policy.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                keys = [key.value for key in node.keys if isinstance(key, ast.Constant)]
                self.assertEqual(len(keys), len(set(keys)))


class PoolStructureTests(unittest.TestCase):
    def test_shared_loader_keeps_aliases_exclusions_and_tier_precedence(self):
        pools = importlib.import_module("repository_pools")
        self.assertEqual(pools.normalize_repos(["PyJWT/jwt", "jpadilla/pyjwt", "pallets/blinker",
                                               "hegel-ai/promptic", "Example/Repo?/skip"]), ["jpadilla/pyjwt"])
        always, rotating = pools.build_tiers()
        self.assertFalse(set(always) & set(rotating))
        self.assertIn("agno-agi/agno", always)
        self.assertIn("python/mypy", rotating)
        self.assertIn("modelcontextprotocol/servers", always)  # read-only watch stays possible

    def test_quality_docs_pool_retains_mypy_exception_and_lane_exclusions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "tools/quality_repos.json").write_text(json.dumps({"watch": [
                {"repo": "Python/Mypy"}, {"repo": "pallets/flask"}, {"repo": "example/local-exclusion"},
                {"repo": "PyJWT/jwt"}, {"repo": "jpadilla/pyjwt"}],
                "blocked": {"repos": ["example/local-exclusion"]}}), encoding="utf-8")
            with patch.object(scan_docs, "ROOT", root):
                self.assertEqual(scan_docs.load_repos(), ["python/mypy", "jpadilla/pyjwt"])

    def test_duplicate_aliases_preserve_stricter_focused_pool_flags(self):
        pools = importlib.import_module("repository_pools")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pool.json"
            path.write_text(json.dumps({"watch": [{"repo": "PyJWT/jwt"},
                {"repo": "jpadilla/pyjwt", "heavy": True, "rust": True}],
                "blocked": {"repos": []}}), encoding="utf-8")
            self.assertEqual(pools.load_quality_pool(path)["watch"],
                             [{"repo": "jpadilla/pyjwt", "heavy": True, "rust": True}])

    def test_legacy_commands_keep_pools_arguments_and_defaults(self):
        pools = importlib.import_module("repository_pools")
        cases = [("scan_agent", [], ["CORE", "WATCH"], 6, {}),
                 ("scan_agent", ["12", "watch"], ["WATCH"], 12, {}),
                 ("scan_agent2", [], ["G"], 6, {}),
                 ("scan_recon2", ["main", "24"], ["MAIN_POOL"], 24, {}),
                 ("scan_recon3", [], ["POOL_B"], 48, {}),
                 ("scan_recon4", [], ["POOL_C"], 48, {}),
                 ("scan_recon5", [], ["POOL_D"], 48, {}),
                 ("scan_recon6", [], ["POOL_E"], 96, {"per_page": 20})]
        for name, args, names, hours, options in cases:
            module = importlib.import_module(name)
            with self.subTest(name=name, args=args), patch.object(module, "scan") as scan, \
                 patch.object(sys, "argv", [name + ".py", *args]):
                module.main()
                self.assertEqual(scan.call_args.args[0], [repo for name in names
                                 for repo in pools.load_pool(name, normalize=False)])
                self.assertEqual(scan.call_args.args[1], hours)
                for key, value in options.items():
                    self.assertEqual(scan.call_args.kwargs[key], value)

    def test_common_legacy_discovery_normalizes_once_and_only_lists_issues(self):
        import scan_pool
        issue = {"number": 3, "title": "Bug: crash", "created_at": "9999-01-01T00:00:00Z",
                 "comments": 0, "labels": [{"name": "bug"}], "assignees": []}
        with patch.object(scan_pool, "api", return_value=[issue]) as api, \
             contextlib.redirect_stdout(io.StringIO()):
            found = scan_pool.scan(["PyJWT/jwt", "jpadilla/pyjwt", "pallets/blinker"], 48, "test")
        self.assertEqual(len(found), 1)
        self.assertEqual(api.call_count, 1)
        self.assertTrue(api.call_args.args[0].startswith("repos/jpadilla/pyjwt/issues?"))

    def test_monitor_does_not_import_executable_pool_scripts(self):
        import monitor_fresh
        original = __import__
        def guarded(name, *args, **kwargs):
            if name.startswith(("scan_agent", "scan_recon")):
                self.fail("pool data must not import executable scanner: " + name)
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded):
            self.assertTrue(monitor_fresh.build_tiers()[0])


if __name__ == "__main__":
    unittest.main()
