"""The RM-vendored fleet scripts must stay importable in this repo (#86)."""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Vendored entry points that hooks run from the repo root. A stale copy of
# agent_check imported shared_scripts.run_mypy_diff and src.contracts, which
# this repo does not ship.
IMPORTABLE_FLEET_MODULES = (
    "scripts.automerge_guard",
    "scripts.requeue_stalled_merges",
    "scripts.pre_push_agent_check",
    "scripts.pre_push_scope",
    "shared_scripts.agent_check",
)


@pytest.mark.parametrize("module", IMPORTABLE_FLEET_MODULES)
def test_vendored_fleet_module_imports_from_repo_root(module):
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
