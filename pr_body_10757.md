`discard()` removes an item from `_data` but leaves its entry in the heap, so the heap keeps a **stale** entry carrying the item's *original* timestamp. Both `purge()` and `pop()` trusted that stale entry:

* `purge()` read the stale timestamp to decide which item expired,
* `pop()` removed the item named by the stale entry.

As a result a re-added item was expired by `purge()` on its old timestamp, evicted first once `maxlen` was reached, and returned first by `pop()` — even though it had just been added. Those entries were only cleaned up when the heap grew more than 15% larger than the data, which for a few re-added items in a set of realistic size never happens.

**Fix:** skip the heap entries that are no longer the item's current entry (compared by identity against `_data`), and drop such entries from the top of the heap before `purge()`'s expiry check, so a re-added item is treated as the newest one.

This matters for the worker's revoked set (`LimitedSet(maxlen=REVOKES_MAX, expires=REVOKE_EXPIRES)`): ids are re-added on every re-revoke and when mingle merges revoked ids from other workers. A re-revoked id could drop out before `REVOKE_EXPIRES` passed since its latest revoke, letting an ETA or countdown task that should stay revoked run.

The regression test covers all three symptoms (expiry, `maxlen` eviction, `pop()`).

Fixes #10757
