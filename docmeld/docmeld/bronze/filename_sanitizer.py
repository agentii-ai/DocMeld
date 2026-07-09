"""Filename sanitization and MD5 hashing for PDF files."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

MAX_STEM_LENGTH = 200

# Characters that are not safe in filenames: anything not alphanumeric or underscore
_UNSAFE = re.compile(r"[^a-z0-9_]+")


def sanitize_stem(stem: str) -> str:
    """Sanitize a filename stem for cross-platform filesystem safety.

    Replaces dangerous characters with underscores, normalizes unicode,
    lowercases, and truncates to MAX_STEM_LENGTH characters.
    """
    # Unicode NFC normalization
    result = unicodedata.normalize("NFC", stem)
    # Lowercase
    result = result.lower()
    # Replace any non-alphanumeric/underscore sequences with single underscore
    result = _UNSAFE.sub("_", result)
    # Collapse multiple underscores
    result = re.sub(r"_+", "_", result)
    # Strip leading/trailing underscores
    result = result.strip("_")
    # Truncate
    if len(result) > MAX_STEM_LENGTH:
        result = result[:MAX_STEM_LENGTH]
    return result


def calculate_hash(pdf_path: str) -> str:
    """Calculate MD5 hash of a file and return last 6 hex digits."""
    md5 = hashlib.md5()
    with open(pdf_path, "rb") as f:
        md5.update(f.read())
    return md5.hexdigest()[-6:]


def get_output_name(pdf_path: str) -> str:
    """Get the sanitized output name with hash suffix.

    Returns: '{sanitized_stem}_{hash6}'
    """
    path = Path(pdf_path)
    stem = sanitize_stem(path.stem)
    hash6 = calculate_hash(pdf_path)
    return f"{stem}_{hash6}"
