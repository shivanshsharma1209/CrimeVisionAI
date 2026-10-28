import tempfile
from pathlib import Path
import pytest
from backend.utils.hashing import calculate_sha256, verify_sha256


def test_sha256_calculation():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("CrimeVision AI Forensic Integrity Verification Test")
        temp_path = f.name

    try:
        hash_val = calculate_sha256(temp_path)
        assert len(hash_val) == 64
        assert isinstance(hash_val, str)
        assert verify_sha256(temp_path, hash_val) is True
        assert verify_sha256(temp_path, "incorrect_hash_value") is False
    finally:
        Path(temp_path).unlink(missing_ok=True)
