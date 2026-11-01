"""Pin and authorize repository regen callbacks for automatic provider hooks."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any


def require(condition: bool, message: str = "Precondition failed") -> None:
    if not condition:
        raise ValueError(message)


def provider_hook_context() -> bool:
    value = os.environ.get("AGENT_CHECK_FROM_PROVIDER_HOOK", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def regen_script_digest(path: Path) -> str:
    require(
        path.is_file() and not path.is_symlink(),
        "regen script must be a regular file",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _allowed_digests(spec: dict[str, Any] | None) -> frozenset[str]:
    if not spec:
        return frozenset()
    raw = spec.get("allowed_sha256")
    if raw is None:
        return frozenset()
    if isinstance(raw, str):
        cleaned = raw.strip().lower()
        return frozenset({cleaned}) if cleaned else frozenset()
    if isinstance(raw, list):
        return frozenset(str(item).strip().lower() for item in raw if str(item).strip())
    return frozenset()


def authorize_repo_regen(
    script: Path,
    spec: dict[str, Any] | None,
    *,
    provider_hook: bool,
) -> tuple[bool, str]:
    if script.is_symlink():
        return False, "repo regen callback must be a regular non-symlink file"
    if not script.is_file():
        return False, "repo regen callback is missing"
    if not provider_hook:
        return True, ""
    allowed = _allowed_digests(spec)
    if not allowed:
        return (
            False,
            "unpinned repo regen callback; add allowed_sha256 to the repo-regen "
            "check in fleet-hooks/manifest.yml",
        )
    digest = regen_script_digest(script)
    if digest not in allowed:
        return False, f"repo regen callback digest mismatch (sha256:{digest})"
    return True, ""
