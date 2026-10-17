<!-- Thank you for sending a PR and taking the time to improve Hydra -->

## Contributor License Agreement

CLA Assistant will check this pull request and provide a signing link if needed.

## Motivation

`instantiate()` crashes with a raw `AttributeError: 'str' object has no attribute 'get'` when call-site keyword arguments override a top-level missing Structured Config. The same call works in Hydra 1.3.

```python
cfg = DictConfig(MISSING, ref_type=Config)
result = instantiate(cfg, count=2, _execution_whitelist_="builtins.dict")
```

`_copy_config_with_override_interpolations()` materializes a `None` root before applying the override overlays, but not a missing one. The overlay code then reads the string backed `MISSING` sentinel as dictionary storage and raises. The caller's config is left missing after the failure.

The fix treats a missing root the same way as a `None` root: build it from `ref_type` (or as an empty dict when there is no structured type) before the overlays are applied, so the overrides land on real storage and the source config is left untouched.

### Have you read the [Contributing Guidelines on pull requests](https://github.com/hydra-ecosystem/hydra/blob/main/CONTRIBUTING.md)?

Yes

### For non-trivial features, API changes, or behavior changes: is there an issue or design discussion where maintainers agreed on the direction?

This restores the documented Hydra 1.3 behavior described in #3542, so no design change is proposed.

## Test Plan

```bash
pytest tests/instantiate/ -q
```

Added `test_callsite_override_materializes_missing_root` next to the existing `test_callsite_override_materializes_none_root`. It instantiates a `DictConfig(MISSING, ref_type=...)` root with `count=2`, asserts the result is `{"count": 2}`, and asserts the source config is still missing.

Discriminating power: with the one-line fix reverted, the new test fails with `AttributeError: 'str' object has no attribute 'get'`, the same error as the issue. With the fix, the full `tests/instantiate/` suite is 1238 passed, 2 skipped.

A news fragment is included in `news/3542.bugfix`.

## Related Issues and PRs

Fixes #3542
