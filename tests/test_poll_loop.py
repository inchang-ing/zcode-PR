"""Run the actual shell loop with a fake poll process and no network or waits."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if os.name == 'nt':
    git = shutil.which('git')
    possible = Path(git).parent.parent / 'bin/bash.exe' if git else Path('missing')
    BASH = str(possible) if possible.exists() else None
else:
    BASH = shutil.which('bash')


@unittest.skipUnless(BASH, 'A native Bash runtime is unavailable')
class PollLoopTests(unittest.TestCase):
    def test_failed_partial_recovered_and_stopped_shifts(self):
        for codes, expected in (([1, 1], 1), ([2, 2], 2), ([1, 0], 0), ([42], 0)):
            with self.subTest(codes=codes), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'output'
                env = dict(os.environ, INTERVAL_SEC='0', DURATION_MIN='1',
                           MAX_ROUNDS=str(len(codes)), GITHUB_OUTPUT=output.as_posix())
                # Override timeout, so the real poll loop runs but Python never does.
                script = ('codes=(' + ' '.join(map(str, codes)) + ')\n'
                          'index=0\n'
                          'timeout() { local rc=${codes[$index]}; index=$((index + 1)); return "$rc"; }\n'
                          'source tools/poll_loop.sh\n')
                result = subprocess.run([BASH, '-c', script], cwd=ROOT, env=env,
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                if codes == [42]:
                    self.assertIn('stopped=true', output.read_text())


if __name__ == '__main__':
    unittest.main()
