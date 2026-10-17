#!/usr/bin/env python3
"""Pool B recon scan: testing / async / packaging / web / data high-profile repos."""
import sys
sys.path.insert(0, r"E:\zcode-PR\.trash")
from scan_recon2 import api, scan  # noqa: E402

POOL_B = [
    "HypothesisWorks/hypothesis", "spulec/freezegun", "getsentry/responses",
    "kevin1024/vcrpy", "samuelcolvin/dirty-equals", "python-trio/trio",
    "MagicStack/asyncpg", "twisted/twisted", "giampaolo/psutil",
    "gorakhargosh/watchdog", "pygments/pygments", "chardet/chardet",
    "dateutil/dateutil", "python-humanize/humanize", "arrow-py/arrow",
    "python-pendulum/pendulum", "prompt-toolkit/python-prompt-toolkit",
    "Delgan/loguru", "hynek/structlog", "getsentry/sentry-python",
    "open-telemetry/opentelemetry-python", "jupyter/nbformat",
    "jupyterlab/jupyterlab", "snakemake/snakemake", "spotify/luigi",
    "jazzband/pip-tools", "pypa/pipx", "pypa/virtualenv", "pypa/packaging",
    "python/importlib_metadata", "gitpython-developers/GitPython",
    "paramiko/paramiko", "pyinvoke/invoke", "tmbo/questionary",
    "coleifer/peewee", "tortoise/tortoise-orm", "piccolo-orm/piccolo",
    "fastapi/sqlmodel", "falconry/falcon", "Pylons/pyramid",
    "Neoteroi/BlackSheep", "spec-first/connexion", "lepture/authlib",
    "jpadilla/pyjwt", "ccxt/ccxt", "freqtrade/freqtrade", "astropy/astropy",
    "geopandas/geopandas", "shapely/shapely", "pymc-devs/pymc",
    "statsmodels/statsmodels", "scikit-image/scikit-image",
]

if __name__ == "__main__":
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    scan(POOL_B, hours, "POOL_B")
