"""Secure serialization and deserialization for OpenFlight capture files.

Replaces unsafe `pickle.load()` with structured, non-executable formats
(JSON with base64 binary encoding and gzip compression support).
Applies Design by Contract (DbC) validation on schemas and boundaries.
"""

from __future__ import annotations

import base64
import gzip
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Magic header prefix for base64 encoded byte payloads in JSON
_B64_PREFIX = "__b64__:"


def _json_encode_helper(obj: Any) -> Any:
    """JSON encoder helper for numpy and binary types."""
    if isinstance(obj, bytes):
        return _B64_PREFIX + base64.b64encode(obj).decode("ascii")
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _json_decode_helper(obj: Any) -> Any:
    """Recursively decode base64 binary values and typed structures from JSON."""
    if isinstance(obj, dict):
        return {k: _json_decode_helper(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_decode_helper(elem) for elem in obj]
    if isinstance(obj, str) and obj.startswith(_B64_PREFIX):
        encoded = obj[len(_B64_PREFIX) :]
        return base64.b64decode(encoded)
    return obj


def validate_capture_schema(data: Any) -> dict[str, Any]:
    """Validate capture dictionary schema per Design by Contract (PP5).

    Precondition: data must be a dictionary with a 'metadata' mapping.
    Postcondition: returns validated dict or raises ValueError.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Capture payload must be a dict, got {type(data).__name__}")
    if "metadata" not in data or not isinstance(data["metadata"], dict):
        raise ValueError("Capture payload must contain a 'metadata' dictionary")
    return data


def save_capture(
    path: str | Path,
    data: dict[str, Any],
    *,
    compress: bool = False,
) -> Path:
    """Save capture data to a secure non-executable JSON or compressed JSON file.

    Parameters
    ----------
    path : str | Path
        Target file path. If ends with .gz or compress=True, writes gzipped JSON.
    data : dict[str, Any]
        Capture dictionary containing metadata and frames/captures.
    compress : bool
        Whether to gzip compress the output file.

    Returns
    -------
    Path
        Path to the saved capture file.
    """
    validate_capture_schema(data)

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    use_gzip = compress or out_path.suffix == ".gz"
    payload = json.dumps(data, default=_json_encode_helper, indent=2 if not use_gzip else None)

    if use_gzip:
        with gzip.open(out_path, "wt", encoding="utf-8") as f:
            f.write(payload)
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(payload)

    logger.debug("Saved secure capture (%d bytes) to %s", out_path.stat().st_size, out_path)
    return out_path


def load_capture(
    path: str | Path,
    *,
    allow_legacy_pickle: bool = False,
) -> dict[str, Any]:
    """Securely load an OpenFlight capture file.

    Parameters
    ----------
    path : str | Path
        Path to capture file (.json, .json.gz, or legacy .pkl).
    allow_legacy_pickle : bool
        If True, permits loading legacy .pkl files. If False and a .pkl file
        is given, raises ValueError with migration instructions.

    Returns
    -------
    dict[str, Any]
        Loaded capture dictionary with decoded binary payloads and metadata.

    Raises
    ------
    FileNotFoundError
        If path does not exist.
    ValueError
        If file is invalid, untrusted pickle format without explicit opt-in,
        or fails schema validation.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Capture file not found: {file_path}")

    suffix = file_path.suffix.lower()

    if suffix == ".pkl":
        if not allow_legacy_pickle:
            raise ValueError(
                f"Refusing to load untrusted pickle file '{file_path.name}'. "
                "Pickle files are executable and pose a security risk. "
                "Migrate this capture using 'python scripts/analysis/migrate_pickles.py' "
                "or explicitly pass '--allow-legacy-pickle' if you trust this local file."
            )
        import pickle  # nosec B301 - guarded behind explicit user flag allow_legacy_pickle

        logger.warning(
            "Loading legacy pickle file with explicit allow_legacy_pickle: %s", file_path
        )
        with open(file_path, "rb") as f:
            raw_data = pickle.load(f)  # nosec B301
        return validate_capture_schema(raw_data)

    if suffix == ".gz" or str(file_path).endswith(".json.gz"):
        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            parsed = json.load(f)
        decoded = _json_decode_helper(parsed)
        return validate_capture_schema(decoded)

    with open(file_path, "r", encoding="utf-8") as f:
        parsed = json.load(f)
    decoded = _json_decode_helper(parsed)
    return validate_capture_schema(decoded)


def migrate_pickle_to_json(
    source_pkl: str | Path,
    target_path: str | Path | None = None,
    *,
    compress: bool = False,
) -> Path:
    """Migrate a legacy pickle capture file to secure JSON format.

    Parameters
    ----------
    source_pkl : str | Path
        Path to existing .pkl capture file.
    target_path : str | Path | None
        Target path for JSON output. If None, replaces .pkl extension with .json (or .json.gz).
    compress : bool
        Whether to compress the output as .json.gz.

    Returns
    -------
    Path
        Path to migrated JSON file.
    """
    src = Path(source_pkl)
    if not src.exists():
        raise FileNotFoundError(f"Source pickle file not found: {src}")

    import pickle  # nosec B301 - local migration utility

    with open(src, "rb") as f:
        data = pickle.load(f)  # nosec B301

    validate_capture_schema(data)

    if target_path is None:
        ext = ".json.gz" if compress else ".json"
        target_path = src.with_suffix(ext)
    else:
        target_path = Path(target_path)

    return save_capture(target_path, data, compress=compress)
