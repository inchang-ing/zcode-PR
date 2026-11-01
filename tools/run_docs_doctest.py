"""Run the >>> examples embedded in markdown docs.

Sphinx doctest builder exists but many projects do not wire it into CI, so the
examples drift. This executes them with the stdlib doctest runner in reading
order, which is how a user would try them.

Usage: python tools/run_docs_doctest.py <docs-dir> [<pkg-src>]
"""
import doctest
import io
import sys
from pathlib import Path

FLAGS = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE | doctest.IGNORE_EXCEPTION_DETAIL


def strip_fences(text):
    """Markdown code fences are not doctest expected output.

    Keeping them makes doctest compare '```' against real output; replace the
    fence lines with blanks so line numbers stay stable.
    """
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("```") or s.startswith(":::"):
            out.append("")
        else:
            out.append(ln)
    return "\n".join(out)


def main():
    docs = Path(sys.argv[1])
    if len(sys.argv) > 2:
        sys.path.insert(0, str(Path(sys.argv[2]).resolve()))
    total_fail = 0
    for p in sorted(docs.glob("*.md")):
        text = strip_fences(p.read_text(encoding="utf-8", errors="replace"))
        if ">>>" not in text:
            continue
        test = doctest.DocTestParser().get_doctest(text, {}, p.stem, str(p), 0)
        if not test.examples:
            continue
        runner = doctest.DocTestRunner(verbose=False, optionflags=FLAGS)
        buf = io.StringIO()
        runner.run(test, out=buf.write)
        if runner.failures:
            total_fail += runner.failures
            print(f"\n===== {p.name}: {runner.failures}/{len(test.examples)} failed =====")
            print(buf.getvalue()[:3000])
        else:
            print(f"{p.name}: {len(test.examples)} examples OK")
    print(f"\nTOTAL FAILURES: {total_fail}")


if __name__ == "__main__":
    main()
