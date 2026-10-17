Resolves: #11130

## Description
`poetry install` rejected valid distribution files when a package's lock entry
recorded more than one hash algorithm (e.g. a mix of `sha256` and `sha512`) and
the index's JSON simple API advertised a higher-priority hash (`sha512`) whose
value differed from the lock while a lower-priority hash (`sha256`) matched.

Root cause: in `Chooser._choose_hash_verified_link` we computed a single
`link_hash` from the highest-priority hash name shared by the lock and the
index, and required that specific value to match. When the chosen name's value
didn't match the lock, the file was skipped even though another advertised hash
did match — so an authentic file was ignored (and `poetry install` failed with
"did not match any known checksums in your lock file").

Fix: accept a match on **any** algorithm the lock also records, instead of only
the single highest-priority one. A distribution is authentic if any of its
advertised hashes matches a hash in the lock.

I added a regression test (`test_chooser_accepts_link_when_any_advertised_hash_matches_lock`)
and verified it fails without the fix (raises `PoetryRuntimeError`) and passes
with it. The full `tests/installation/test_chooser.py` suite passes (63 passed).

## Check List
- [x] Added **tests** for changed code.
- [ ] Updated **documentation** for changed code. (internal behavior fix, no docs change)
