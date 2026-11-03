"""Read the plain-text settings file (config.txt) into a dictionary.

Every line is "key = value"; lines starting with # are comments.
Unknown keys and bad numbers stop the program with a clear message
instead of being ignored silently.
"""

import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_DIR, "config.txt")

SOURCES = ("demo", "airlabs")

DEFAULTS = {
    "source": "demo",
    "api_key_env": "AIRLABS_API_KEY",
    "ntfy_server": "https://ntfy.sh",
    "ntfy_topic": "",
    "ntfy_token_env": "NTFY_TOKEN",
    "delay_threshold_min": 15,
    "delay_step_min": 15,
    "poll_interval_sec": 300,
    "max_requests_per_month": 900,
    "flights_file": "flights.json",
    "state_file": "state.json",
    "log_file": "alerts_log.txt",
    "demo_file": "demo_data.json",
}

# Smallest accepted value for every number setting.
NUMBER_MINIMUMS = {
    "delay_threshold_min": 1,
    "delay_step_min": 1,
    "poll_interval_sec": 30,
    "max_requests_per_month": 1,
}

PATH_KEYS = ("flights_file", "state_file", "log_file", "demo_file")


# ---------- helper functions ----------

def parse_line(line):
    """Return (key, value) for a "key = value" line, or None for blanks and comments."""
    text = line.strip()
    if text == "" or text.startswith("#"):
        return None
    if "=" not in text:
        raise ValueError(f'expected "key = value" but found "{text}"')
    key, value = text.split("=", 1)
    return key.strip().lower(), value.strip()


def to_number(key, value):
    """Turn a setting into a whole number and check its minimum."""
    if not value.isdigit():
        raise ValueError(f"{key} must be a whole number, not '{value}'")
    number = int(value)
    if number < NUMBER_MINIMUMS[key]:
        raise ValueError(f"{key} must be at least {NUMBER_MINIMUMS[key]}")
    return number


def check_topic(topic):
    """An ntfy topic is one word of letters, digits, - and _ (it becomes part of a URL)."""
    for char in topic:
        if not (char.isascii() and (char.isalnum() or char in "-_")):
            raise ValueError(f"ntfy_topic may only contain letters, digits, - and _ (found '{char}')")


def resolve_path(path, config_dir):
    """Relative file names are read next to the config file."""
    if os.path.isabs(path):
        return path
    return os.path.join(config_dir, path)


# ---------- main function of this module ----------

def load_config(path=DEFAULT_CONFIG_PATH):
    """Read config.txt and return a complete settings dictionary."""
    if not os.path.isfile(path):
        raise ValueError(f"config file not found: {path}")

    settings = dict(DEFAULTS)
    line_number = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line_number += 1
            try:
                pair = parse_line(line)
                if pair is None:
                    continue
                key, value = pair
                if key not in DEFAULTS:
                    raise ValueError(f"unknown setting '{key}'")
                if key in NUMBER_MINIMUMS:
                    value = to_number(key, value)
            except ValueError as error:
                raise ValueError(f"{os.path.split(path)[1]} line {line_number}: {error}")
            settings[key] = value

    if settings["source"] not in SOURCES:
        raise ValueError(f"source must be one of {', '.join(SOURCES)}, not '{settings['source']}'")
    check_topic(settings["ntfy_topic"])
    settings["ntfy_server"] = settings["ntfy_server"].rstrip("/")

    config_dir = os.path.dirname(os.path.abspath(path))
    for key in PATH_KEYS:
        settings[key] = resolve_path(settings[key], config_dir)
    return settings
