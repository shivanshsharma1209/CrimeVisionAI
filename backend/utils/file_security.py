import os
import re
import uuid
import mimetypes
from pathlib import Path
from werkzeug.utils import secure_filename
from config import Config

MIME_TYPE_MAPPING = {
    # Images
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    # Videos
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    # Audio
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
}


def get_file_extension(filename: str) -> str:
    """Return lowercase extension including leading dot, e.g. '.jpg'"""
    _, ext = os.path.splitext(filename)
    return ext.lower()


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is among allowed forensic media formats."""
    ext = get_file_extension(filename).lstrip(".")
    return ext in Config.ALLOWED_EXTENSIONS


def classify_media_type(filename: str) -> str:
    """Return 'image', 'video', 'audio', or 'unknown' based on extension."""
    ext = get_file_extension(filename).lstrip(".")
    if ext in Config.ALLOWED_IMAGE_EXTENSIONS:
        return "image"
    elif ext in Config.ALLOWED_VIDEO_EXTENSIONS:
        return "video"
    elif ext in Config.ALLOWED_AUDIO_EXTENSIONS:
        return "audio"
    return "unknown"


def detect_mime_type(file_path: Path, filename: str) -> str:
    """Detect MIME type using file extension mapping or mimetypes module."""
    ext = get_file_extension(filename)
    if ext in MIME_TYPE_MAPPING:
        return MIME_TYPE_MAPPING[ext]
    mime, _ = mimetypes.guess_type(str(file_path))
    return mime or "application/octet-stream"


def generate_secure_storage_name(original_filename: str) -> str:
    """
    Generate a non-colliding, safe storage name (UUID4 + sanitized extension).
    Prevents directory traversal, encoding issues, and collision.
    """
    clean_name = secure_filename(original_filename)
    _, ext = os.path.splitext(clean_name)
    if not ext:
        ext = get_file_extension(original_filename)
    unique_id = uuid.uuid4().hex
    return f"{unique_id}{ext.lower()}"


def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """Ensure target path does not escape the base directory (prevent path traversal)."""
    try:
        resolved_base = base_dir.resolve()
        resolved_target = target_path.resolve()
        return resolved_base in resolved_target.parents or resolved_base == resolved_target
    except Exception:
        return False
