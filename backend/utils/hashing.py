import hashlib
from pathlib import Path
from typing import Union


def calculate_sha256(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """
    Calculate SHA-256 hash of a file efficiently by reading in chunks.
    Ensures low memory footprint for large video and audio files.
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found for hashing: {file_path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_sha256(file_path: Union[str, Path], expected_hash: str) -> bool:
    """Verify that file's SHA-256 hash matches the expected hash."""
    actual_hash = calculate_sha256(file_path)
    return actual_hash.lower() == expected_hash.strip().lower()
