"""Tests for openflight.capture_io secure serialization and deserialization."""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pytest

from openflight.capture_io import (
    load_capture,
    migrate_pickle_to_json,
    save_capture,
    validate_capture_schema,
)


@pytest.fixture
def sample_capture_data() -> dict:
    return {
        "metadata": {
            "orientation": "horizontal",
            "club": "7-iron",
            "sample_rate": 30000,
            "gain": 12,
            "numpy_float": np.float64(42.5),
            "numpy_int": np.int32(100),
        },
        "frames": [
            {
                "timestamp": 123.456,
                "radc": b"\x00\x01\x02\x03\xff\xfe\xfd\xfc" * 384,
                "tdat": {"range_m": 2.5, "speed_mps": 45.2},
                "pdat": [{"range_m": 2.5, "speed_mps": 45.2}],
            }
        ],
        "ops243_shots": [{"timestamp": 123.45, "ball_speed_mph": 120.5, "club_speed_mph": 85.2}],
        "numpy_array": np.array([1.0, 2.0, 3.5]),
    }


def test_save_and_load_capture_roundtrip_json(tmp_path: Path, sample_capture_data: dict):
    out_file = tmp_path / "capture.json"
    saved_path = save_capture(out_file, sample_capture_data)

    assert saved_path.exists()
    loaded = load_capture(saved_path)

    assert loaded["metadata"]["orientation"] == "horizontal"
    assert loaded["metadata"]["club"] == "7-iron"
    assert loaded["metadata"]["sample_rate"] == 30000
    assert loaded["metadata"]["numpy_float"] == 42.5
    assert loaded["metadata"]["numpy_int"] == 100
    assert len(loaded["frames"]) == 1
    assert loaded["frames"][0]["timestamp"] == 123.456
    assert loaded["frames"][0]["radc"] == sample_capture_data["frames"][0]["radc"]
    assert isinstance(loaded["frames"][0]["radc"], bytes)
    assert loaded["frames"][0]["tdat"]["range_m"] == 2.5
    assert loaded["ops243_shots"][0]["ball_speed_mph"] == 120.5
    assert loaded["numpy_array"] == [1.0, 2.0, 3.5]


def test_save_and_load_capture_roundtrip_gzip(tmp_path: Path, sample_capture_data: dict):
    out_file = tmp_path / "capture.json.gz"
    saved_path = save_capture(out_file, sample_capture_data, compress=True)

    assert saved_path.exists()
    loaded = load_capture(saved_path)

    assert loaded["metadata"]["orientation"] == "horizontal"
    assert loaded["frames"][0]["radc"] == sample_capture_data["frames"][0]["radc"]
    assert isinstance(loaded["frames"][0]["radc"], bytes)


def test_load_legacy_pickle_allowed_with_flag(tmp_path: Path, sample_capture_data: dict):
    pkl_file = tmp_path / "legacy_capture.pkl"
    with open(pkl_file, "wb") as f:
        pickle.dump(sample_capture_data, f)

    loaded = load_capture(pkl_file, allow_legacy_pickle=True)
    assert loaded["metadata"]["orientation"] == "horizontal"
    assert loaded["frames"][0]["timestamp"] == 123.456


def test_load_legacy_pickle_rejected_by_default(tmp_path: Path, sample_capture_data: dict):
    pkl_file = tmp_path / "insecure_capture.pkl"
    with open(pkl_file, "wb") as f:
        pickle.dump(sample_capture_data, f)

    with pytest.raises(ValueError, match="Refusing to load untrusted pickle file"):
        load_capture(pkl_file, allow_legacy_pickle=False)


def test_load_nonexistent_file_raises_filenotfound(tmp_path: Path):
    nonexistent = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        load_capture(nonexistent)


def test_schema_validation_preconditions():
    with pytest.raises(ValueError, match="Capture payload must be a dict"):
        validate_capture_schema(["not", "a", "dict"])

    with pytest.raises(ValueError, match="must contain a 'metadata' dictionary"):
        validate_capture_schema({"no_metadata": 123})

    with pytest.raises(ValueError, match="must contain a 'metadata' dictionary"):
        validate_capture_schema({"metadata": "not_a_dict"})


def test_migrate_pickle_to_json(tmp_path: Path, sample_capture_data: dict):
    pkl_file = tmp_path / "legacy.pkl"
    with open(pkl_file, "wb") as f:
        pickle.dump(sample_capture_data, f)

    target_json = migrate_pickle_to_json(pkl_file)
    assert target_json.exists()
    assert target_json.suffix == ".json"

    loaded = load_capture(target_json)
    assert loaded["metadata"]["orientation"] == "horizontal"
    assert loaded["frames"][0]["radc"] == sample_capture_data["frames"][0]["radc"]
