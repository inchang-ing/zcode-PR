"""Discrimination test for alembic#1607.

Reproduces the MariaDB false-positive: a computed column whose metadata model
renders ``TRUE`` while the reflected DB column renders ``1``. The fixed
``_normalize_computed_default`` must treat them as equivalent (no warning); the
old normalizer produced a spurious "cannot be modified" warning.
"""
import re
from types import SimpleNamespace

from sqlalchemy import Column
from sqlalchemy import Computed
from sqlalchemy import Boolean
from sqlalchemy.engine import default

import alembic.autogenerate.compare.server_defaults as sd
from alembic.operations import ops

metadata_col = Column(
    "is_active_record",
    Boolean,
    Computed("CASE WHEN deleted_at IS NULL THEN TRUE ELSE NULL END"),
)
conn_col = Column(
    "is_active_record",
    Boolean,
    Computed("CASE WHEN deleted_at IS NULL THEN 1 ELSE NULL END"),
)
ac = SimpleNamespace(dialect=default.DefaultDialect())


def _run():
    calls = []
    sd.util.warn = lambda msg, *a, **k: calls.append(msg)
    alter = ops.AlterColumnOp("record_with_computed", "is_active_record", schema=None)
    sd._compare_computed_default(
        ac, alter, None, "record_with_computed", "is_active_record", conn_col, metadata_col
    )
    return calls


# 1) With the FIXED normalizer -> no warning.
fixed = _run()
assert not fixed, f"FIXED should not warn, got: {fixed}"
print("OK: fixed normalizer -> no spurious warning (TRUE == 1)")


# 2) With the OLD normalizer -> warning (confirms the bug the fix addresses).
def _old_normalize(sqltext: str) -> str:
    return re.sub(r"[ \(\)'\"`\[\]\t\r\n]", "", sqltext).lower()


sd._normalize_computed_default = _old_normalize
buggy = _run()
assert buggy, "OLD normalizer should have produced a warning"
print(f"CONFIRMED: old normalizer warns -> {buggy[0]!r}")
print("DISCRIMINATION PASS")
