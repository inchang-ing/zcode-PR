#!/usr/bin/env python3
"""Pool C recon scan: another batch of high-profile, mostly pure-Python projects."""
import sys
sys.path.insert(0, r"E:\zcode-PR\.trash")
from scan_recon2 import api, scan  # noqa: E402

POOL_C = [
    "ibis-project/ibis", "narwhals-dev/narwhals", "pydata/xarray",
    "zarr-developers/zarr-python", "scikit-hep/uproot", "Netflix/metaflow",
    "sktime/sktime", "dask/distributed", "pytest-dev/pytest-bdd",
    "pytest-dev/pytest-cov", "PyCQA/bandit", "PyCQA/flake8", "PyCQA/isort",
    "python-attrs/cattrs", "mkdocs/mkdocs", "squidfunk/mkdocs-material",
    "executablebooks/myst-parser", "jupyter/nbconvert",
    "jupyter-server/jupyter_server", "holoviz/panel", "zauberzeug/nicegui",
    "docker/docker-py", "microsoft/playwright-python", "SeleniumHQ/selenium",
    "robotframework/robotframework", "joke2k/faker", "FactoryBoy/factory_boy",
    "syrupy-project/syrupy", "15r10nk/inline-snapshot", "biopython/biopython",
    "pydicom/pydicom", "bashtage/linearmodels", "bashtage/arch",
    "apache/iceberg-python", "delta-io/delta-rs", "modin-project/modin",
    "graphql-python/graphene", "mirumee/ariadne", "python/typeshed",
    "hynek/stamina", "pydoit/doit", "nteract/papermill", "unit8co/darts",
    "awslabs/gluonts", "scikit-hep/awkward", "python-poetry/cleo",
]

if __name__ == "__main__":
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    scan(POOL_C, hours, "POOL_C")
