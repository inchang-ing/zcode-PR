## Description

`dask.array.shuffle` raised `ValueError: Array chunk size or shape is unknown` (wrapping an `IndexError` from `dask.array.chunk.getitem`) for arrays whose length along the shuffled axis exceeded 255.

**Root cause:** in `dask/array/_shuffle.py`, the integer dtype used for the taker indices and the argsort positions was derived from the per-chunk size (`max(*chunks[axis], chunk_size_limit)`). Those positions range over the **whole** axis length, not a single chunk, so for any axis longer than 255 elements the `uint8` dtype overflowed. The corrupted positions then mapped elements to the wrong source chunk, producing out-of-range local indices and the error above.

**Fix:** derive the dtype from the total axis length (`sum(chunks[axis])`) so it spans every possible position. For small arrays this still resolves to `uint8` (see `test_dtype_taker`), so existing behaviour is unchanged there.

- [x] Closes #12632
- [x] Tests added / passed
- [x] Passes `pixi run lint`

The new regression test `test_shuffle_indexer_larger_than_uint8` reproduces the issue's MRE (10_000 elements along the axis) and fails before the fix with the exact reported error.
