## Linked Issue

Closes #7612

## Description

After a memory expires, an inferred `add()` of the same fact with a future
`expiration_date` returned an empty `results` list and left no visible memory.

`Memory._add_to_vector_store()` and `AsyncMemory._add_to_vector_store()` take the
Phase 1 `vector_store.search()` results and use them for two things:

1. the `## Existing Memories` section of the extraction prompt, and
2. the `existing_hashes` set that suppresses duplicate writes (Phase 5).

Neither applied the expiration predicate the SDK already uses to hide expired
memories in `get_all()` and `search()` (`_payload_is_expired`). So an expired
copy was presented to the LLM as a live fact *and* its content hash suppressed
the fresh write, even though the caller supplied a valid future expiry.

This changes one line per API: expired records are filtered out of the Phase 1
retrieval results, so both downstream consumers only see live memories.

```python
existing_results = [mem for mem in existing_results if not _payload_is_expired(getattr(mem, "payload", None))]
```

`getattr(mem, "payload", None)` mirrors the `hasattr(mem, "payload")` guard the
existing hash loop already uses, and `_payload_is_expired(None)` returns `False`,
so records without a payload keep their current behaviour.

Scope: only the two inferred write paths. Unexpired duplicates and within-batch
duplicates are still deduplicated, `infer=False` writes are untouched, and old
expired rows are preserved for `show_expired=True` — nothing is deleted or
rewritten.

## Type of Change

- [x] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Refactor (no functional changes)
- [ ] Documentation update

## AI Assistance

<!-- This is about the code, not this description. Writing the description with AI is fine. -->

- [ ] No AI assistance
- [ ] AI-assisted (autocomplete, or I asked a model questions while writing this)
- [x] AI-generated (an agent wrote most or all of this diff)

Tool: CodeBuddy Code (Claude), driving `gh`/`git`/`pytest` locally.

What I did myself, beyond running the agent:

- Re-ran the issue's reproduction script against the unmodified checkout and
  confirmed the six reported outcomes before touching any code.
- Read the two call sites and confirmed `existing_results` feeds only the
  extraction prompt and the hash-dedup set (grep), which is why filtering at the
  retrieval point is safe.
- Ran the fix/revert/restore cycle twice — on the reproduction script and on the
  new unit tests — to confirm the tests are discriminating rather than merely
  passing.
- Diffed the whole-suite failure set before and after the change to show it is
  unchanged.
- Ran `ruff check` (0.16.0, the version `pyproject.toml` pins) on both files.

- [x] **I can explain every line of this diff and how it interacts with the rest of the codebase, without asking an AI tool.**

## Breaking Changes

N/A

## Test Coverage

- [x] I added/updated unit tests
- [ ] I added/updated integration tests
- [x] I tested manually (describe below)
- [ ] No tests needed (explain why)

### Unit tests (deterministic, no network)

`tests/memory/test_main.py::TestExpiredExistingMemoriesDoNotBlockAdd` — 4 tests,
LLM, embedder and vector store are all mocked; entity extraction is stubbed out.

| Test | Without fix | With fix |
| --- | --- | --- |
| `test_expired_copy_does_not_suppress_fresh_add` | FAIL | PASS |
| `test_async_expired_copy_does_not_suppress_fresh_add` | FAIL | PASS |
| `test_unexpired_duplicate_is_still_deduplicated` | PASS | PASS |
| `test_async_unexpired_duplicate_is_still_deduplicated` | PASS | PASS |

The two control tests are deliberate: they pin the behaviour that must *not*
change, so an over-broad "just disable dedup" patch fails the suite.

The expired tests assert three separate things: the memory is written, the store
`insert` happened once, and the fact is absent from the `## Existing Memories`
section of the captured prompt.

### Manual verification (the issue's own reproducer)

Saved the issue's script unmodified (only the interpreter path changed) and ran
all six API × case combinations against the checkout, with real local on-disk
Qdrant and SQLite and deterministic LLM/embedding doubles.

`--case expired`, before the fix — reproduces the report exactly:

```text
first ADD: 1
visible before: 0
second ADD: 0
visible after: 0
searchable after: 0
stored expirations: ['2000-01-01']
fact in second Existing Memories: True
AssertionError: An expired copy suppressed the new unexpired memory
```

`--case expired`, after the fix (identical for `--api sync` and `--api async`):

```text
first ADD: 1
visible before: 0
second ADD: 1
visible after: 1
searchable after: 1
stored expirations: ['2000-01-01', '2999-01-01']
fact in second Existing Memories: False
```

The four control runs (`active` and `raw`, both APIs) pass before and after, with
unchanged output. Note `stored expirations` keeps the old `2000-01-01` row, so
`show_expired=True` history is preserved.

### Discriminating power

Fix applied → PASS; fix reverted (`git stash`) → FAIL; fix restored → PASS. Done
for both the reproduction script and the unit tests. A passing suite alone would
not have shown this, so the revert step is the actual evidence.

### Regression runs

- `pytest tests/memory/test_main.py tests/memory/test_storage.py -q` → **75 passed**
  (71 before this PR + the 4 new tests). This is the baseline suite the issue cites.
- `ruff check mem0/memory/main.py tests/memory/test_main.py` → **All checks passed**
  (ruff 0.16.0, the pinned version). `ruff format --check` reports both files as
  needing reformatting, but it reports the same on unmodified `main`, so that is
  pre-existing and not from this diff.
- Broader run over the collectible suite: failure set is byte-identical before and
  after the change (159 pre-existing failures/errors, 0 new). Those are all
  environment artifacts of this machine — missing optional provider packages
  (`tests/llms`, `tests/vector_stores`, `tests/embeddings`), missing server deps
  (`tests/test_server_*`), and `tests/test_oss_to_platform_migrate.py` needing
  `python3`, which this sandbox blocks. I did not install around them.

## Checklist

- [x] My code follows the project's style guidelines
- [x] I have performed a self-review of my code
- [x] I have added tests that prove my fix/feature works
- [x] New and existing tests pass locally
- [x] I have updated documentation if needed (none needed — behaviour now matches what the `add()` docstring already promises)

---

Two notes for the maintainers, since both affect how you may want to handle this:

1. **#7612 does not carry the `accepted` label**, so I expect the PR Gate to close
   this automatically. That is the documented path and I am not asking for an
   exception — it reopens by itself if the label is applied. I would still
   appreciate the `accepted` decision on the issue, since the reporter asked for
   confirmation of the intended lifecycle semantics before anyone wrote a patch,
   and that question is still unanswered.

2. **@junnhwan commented on the issue saying they planned to contribute this fix.**
   They have no open pull request in the repo, and @Tirthnp replied "All yours",
   so I went ahead rather than let it stall. If @junnhwan has work in progress,
   I am happy to close this in favour of theirs — just say so.
