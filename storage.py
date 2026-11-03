"""Safe file helpers for the saved state (W4: "Protect state").

- write_text_safely: a crash while writing never leaves a half-written file.
- load_json: a broken file is kept as evidence and the .bak copy is used.
"""

import json
import os
import shutil
from datetime import datetime, timezone


def now_utc():
    """Current time as an aware UTC timestamp, e.g. 2026-11-03T14:05:00+00:00 (W4: aware datetimes)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_text_safely(path, text):
    """Write to a temporary file, keep the old file as .bak, then move the new one into place."""
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    if os.path.isfile(path):
        shutil.copy(path, path + ".bak")
    shutil.move(temp_path, path)


def read_json(path):
    """Parse one JSON file."""
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_json(path, default):
    """Return (data, warning). A missing file gives default; a broken one falls back to its .bak copy."""
    if not os.path.isfile(path):
        return default, ""
    try:
        return read_json(path), ""
    except (ValueError, OSError) as error:  # a JSON syntax error is a ValueError
        problem = f"{os.path.split(path)[1]} could not be read ({type(error).__name__})"

    # Keep the broken file as evidence instead of overwriting it (W4: keep evidence).
    shutil.copy(path, path + ".broken")
    backup = path + ".bak"
    if os.path.isfile(backup):
        try:
            data = read_json(backup)
            shutil.copy(backup, path)
            return data, problem + "; restored the .bak copy (broken file kept as .broken)"
        except (ValueError, OSError):
            pass
    return default, problem + "; starting empty (broken file kept as .broken)"
