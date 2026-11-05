"""Invalid preparation limits must fail before reading candidates or state."""
import contextlib
import io
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import auto_run as auto


class AutoRunCLITests(unittest.TestCase):
    def test_invalid_limits_and_unknown_options_fail_before_inputs(self):
        cases = (["--max=oops"], ["--max=-1"], ["--max=1.5"], ["--max"],
                 ["--per-repo=oops"], ["--per-repo=-1"], ["--per-repo"],
                 ["--unknown"], ["--ma=1"], ["--dry-run=false"])
        for argv in cases:
            with self.subTest(argv=argv), \
                    patch.object(auto, "load_candidates", return_value=[]) as load, \
                    patch.object(auto, "DispatchedStore") as store, \
                    patch.object(auto, "run") as run, \
                    patch.object(sys, "argv", ["auto_run.py", *argv]), \
                    contextlib.redirect_stderr(io.StringIO()), \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    auto.main()
                self.assertEqual(result.exception.code, 2)
                load.assert_not_called()
                store.assert_not_called()
                run.assert_not_called()

    def invoke(self, argv):
        candidates = [auto.Candidate(repo, number, "bug: crash", "")
                      for repo, number in (("a/b", 1), ("a/b", 2), ("c/d", 1), ("c/d", 2))]
        store = SimpleNamespace(is_active=lambda key: False, repo_inflight=lambda repo: False)
        with patch.object(auto, "load_candidates", return_value=candidates), \
                patch.object(auto, "DispatchedStore", return_value=store), \
                patch.dict(auto.REPROS, {c.key: lambda c, p: False for c in candidates}, clear=True), \
                patch.dict(auto.FIXERS, {}, clear=True), \
                patch.object(auto, "run") as run, \
                contextlib.redirect_stdout(io.StringIO()):
            auto.main(argv)
        return [(call.args[0].key, call.kwargs["dry_run"]) for call in run.call_args_list]

    def test_valid_limits_defaults_and_zero_keep_preparation_behavior(self):
        cases = (([], ["a/b#1", "c/d#1"]),
                 (["--max=1"], ["a/b#1"]),
                 (["--per-repo=2"], ["a/b#1", "a/b#2", "c/d#1", "c/d#2"]),
                 (["--per-repo", "2", "--max", "3"], ["a/b#1", "a/b#2", "c/d#1"]),
                 (["--max=0"], []), (["--per-repo=0"], []))
        for argv, expected in cases:
            with self.subTest(argv=argv):
                self.assertEqual(self.invoke(argv), [(key, False) for key in expected])

    def test_dry_run_keeps_limits_and_reaches_runner_as_dry(self):
        self.assertEqual(self.invoke(["--dry-run", "--max=1"]), [("a/b#1", True)])
        self.assertEqual(self.invoke(["--dry-run", "--max=0"]), [])

    def test_explicit_argv_does_not_use_process_arguments(self):
        with patch.object(sys, "argv", ["auto_run.py", "--max=0"]):
            self.assertEqual(self.invoke(["--max=1"]), [("a/b#1", False)])


if __name__ == "__main__":
    unittest.main()
