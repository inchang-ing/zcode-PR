"""Review repro for truera/trulens#3052 (Abelo9996's should-fix).

Round-trips a parquet `list<timestamp[ns]>` column through the exact curation
helpers this PR touched.

Expected on the CURRENT branch (`.tolist()` path): elements come back as int
nanoseconds, so `_normalize_text` stores `1704067200000000000` where an
equivalent Python list would store an ISO timestamp -> different ground truth
id for the same logical value.
"""
import datetime
import json
import os
import tempfile

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from trulens.core.dataset import _as_elements, _normalize_text

t1 = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
work = tempfile.mkdtemp()
path = os.path.join(work, "t.parquet")
col = pa.array([[t1], [t1, t1]], type=pa.list_(pa.timestamp("ns")))
pq.write_table(pa.table({"ctx": col}), path)
value = pd.read_parquet(path)["ctx"].iloc[1]

print("cell type:", type(value).__name__)
print("element types:", [type(e).__name__ for e in value])
elements = _as_elements(value)
print("_as_elements ->", elements)
print("python list would serialize ->", json.dumps([str(t1), str(t1)]))
print("_normalize_text ->", _normalize_text(value)[:140])
print("pd.Series(...).tolist() ->", pd.Series(value).tolist())
