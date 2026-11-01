"""Audit docstrings against real signatures.

Finds the "documented but does not exist" class of error: a docstring
documents a parameter the function no longer takes (renamed / removed
without updating the docs). This kind of defect is essentially uncontested
because nobody files an issue for it.

Usage: python tools/docstring_audit.py <repo-dir> [<repo-dir> ...]
"""
import ast
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".tox", ".venv", "venv", "build", "dist", "node_modules",
             "__pycache__", ".eggs", "site-packages", "tests", "test", "testing"}

SPHINX = re.compile(r"^\s*:param\s+(?:[\w\[\], \.]+?\s+)?(\*{0,2}\w+)\s*:", re.M)
GOOGLE_HEAD = re.compile(r"^\s*(Args|Arguments|Parameters|Keyword Args|Other Parameters)\s*:\s*$", re.M)
NUMPY_HEAD = re.compile(r"^\s*(Parameters|Other Parameters)\s*\n\s*-{3,}\s*$", re.M)
GOOGLE_ITEM = re.compile(r"^(\s+)(\*{0,2}\w+)\s*(?:\([^)]*\))?\s*:", re.M)
NUMPY_ITEM = re.compile(r"^(\*{0,2}\w+)\s*:\s*[\w\[\], \.\|]+$", re.M)


def sig_names(node):
    a = node.args
    names = [x.arg for x in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)]
    if a.vararg:
        names.append(a.vararg.arg)
    if a.kwarg:
        names.append(a.kwarg.arg)
    return [n for n in names if n not in ("self", "cls")]


def documented(doc):
    names = set()
    for m in SPHINX.finditer(doc):
        names.add(m.group(1).lstrip("*"))
    for head_re, item_re, end_marker in ((GOOGLE_HEAD, GOOGLE_ITEM, "args"),
                                        (NUMPY_HEAD, NUMPY_ITEM, "numpy")):
        for h in head_re.finditer(doc):
            rest = doc[h.end():]
            lines = rest.splitlines()
            block = []
            for ln in lines:
                if not ln.strip():
                    if block:
                        block.append(ln)
                        continue
                    break
                if h.re is GOOGLE_HEAD and not ln.startswith((" ", "\t")):
                    break
                if h.re is GOOGLE_HEAD and block and not ln.startswith((" ", "\t")):
                    break
                block.append(ln)
                if len(block) > 60:
                    break
            text = "\n".join(block)
            if end_marker == "args":
                # stop at the next section header at column 0-ish
                cut = re.search(r"^\s*(Returns|Raises|Yields|Example|Examples|Note|Notes|Attributes|See Also)\s*:", text, re.M)
                if cut:
                    text = text[:cut.start()]
            for m in item_re.finditer(text):
                names.add(m.group(2).lstrip("*"))
    return names


def audit_file(p: Path, out):
    try:
        tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        doc = ast.get_docstring(node)
        if not doc:
            continue
        real = sig_names(node)
        if not real and not node.args.args:
            continue
        if any(x.arg in ("**kwargs", "*args") for x in []):
            continue
        real_set = set(real)
        has_var_kw = node.args.kwarg is not None
        has_var_pos = node.args.vararg is not None
        docs = documented(doc)
        ghost = sorted(docs - real_set)
        # filter obvious false friends
        ghost = [g for g in ghost if g not in ("return", "returns", "rtype", "raises", "yields",
                                               "type", "default", "optional", "note", "todo")]
        if ghost:
            out.append({"file": str(p), "line": node.lineno, "func": node.name,
                        "ghost": ghost, "real": real,
                        "var_kw": has_var_kw, "var_pos": has_var_pos})


def main():
    results = []
    for d in sys.argv[1:]:
        root = Path(d)
        if not root.exists():
            print("missing", d)
            continue
        for p in root.rglob("*.py"):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            audit_file(p, results)
    results.sort(key=lambda r: (r["file"], r["line"]))
    for r in results:
        flag = ""
        if r["var_kw"]:
            flag = "  [**kwargs -> likely false positive]"
        print(f"{r['file']}:{r['line']} {r['func']}  ghost={r['ghost']} real={r['real']}{flag}")
    print(f"\n{len(results)} suspicious docstrings")


if __name__ == "__main__":
    main()
