"""
Shared fixtures. Real-SGCC-backed tests need the actual ~160MB CSV, which
isn't committed to this repo (see data/README.md) -- they skip gracefully
via `real_sgcc_csv_path` below rather than failing for anyone who hasn't
downloaded it.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def real_sgcc_csv_path() -> str:
    """Path to the real SGCC CSV, from the TRIPWIRE_SGCC_CSV env var.

    Skips the test (not a failure) if the env var isn't set or the file
    doesn't exist -- this is expected for anyone who hasn't downloaded the
    dataset yet. Set it, e.g. on Windows:

        set TRIPWIRE_SGCC_CSV=C:\\path\\to\\data set.csv
    """
    path = os.environ.get("TRIPWIRE_SGCC_CSV")
    if not path or not Path(path).exists():
        pytest.skip(
            "real SGCC CSV not available -- set the TRIPWIRE_SGCC_CSV env var "
            "to its path to run tests against the real dataset (see data/README.md)"
        )
    return path
