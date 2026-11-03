"""Get the current facts for one flight from the chosen source.

demo    - demo_data.json, no network (safe for the presentation)
airlabs - AirLabs schedules API over HTTPS; the key is read from an environment variable

Every fetcher returns the same result dictionary, so the rest of the program
does not care where the data came from.
"""

import json
import os
import time

import requests

from records import make_record

AIRLABS_URL = "https://airlabs.co/api/v9/schedules"
TIMEOUT_SEC = 10
RETRY_WAITS = (1, 2)          # 3 tries in total: wait 1 s, then 2 s (W4: retry budget + backoff)
MAX_RETRY_AFTER_SEC = 60      # a longer Retry-After means: stop for now


def new_result():
    """record: the flat record or None; requests: API calls used; stop: end the round (access problem)."""
    return {"record": None, "error": "", "requests": 0, "stop": False}


# ---------- HTTP with retries ----------

def get_json_with_retry(url, params):
    """GET a JSON answer. Return (data, error, requests_used, stop).

    Retried: timeouts, network errors, 5xx and 429 with a short Retry-After.
    Not retried: 401/403 (stop and fix the key) and other 4xx (W4: stop on refusal).
    """
    used = 0
    error = ""
    for attempt in range(len(RETRY_WAITS) + 1):
        used += 1
        wait = 0
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT_SEC)
        except requests.exceptions.RequestException as exc:
            # Only the error type: the full message could contain the URL with the key.
            error = f"network problem ({type(exc).__name__})"
        else:
            status = response.status_code
            if status == 200:
                try:
                    return response.json(), "", used, False
                except ValueError:
                    return None, "the answer is not JSON", used, False
            if status in (401, 403):
                return None, f"access denied (HTTP {status}) - check the API key", used, True
            if status == 429:
                retry_after = response.headers.get("Retry-After", "")
                if not retry_after.isdigit() or int(retry_after) > MAX_RETRY_AFTER_SEC:
                    return None, "rate limit reached (HTTP 429) - try again later", used, True
                wait = int(retry_after)  # W4: wait as Retry-After says
                error = "rate limited (HTTP 429)"
            elif status >= 500:
                error = f"server error (HTTP {status})"
            else:
                return None, f"request rejected (HTTP {status})", used, False
        if attempt < len(RETRY_WAITS):
            time.sleep(max(wait, RETRY_WAITS[attempt]))
    return None, f"{error} after {used} tries", used, False


# ---------- AirLabs ----------

def pick_entry(entries):
    """Several schedule rows can match; prefer one that has not landed yet."""
    for entry in entries:
        if type(entry) == dict and entry.get("status") in ("scheduled", "active"):
            return entry
    for entry in entries:
        if type(entry) == dict:
            return entry
    return None


def fetch_airlabs(flight, settings, step):
    """Ask AirLabs for one flight (step is only used by the demo source)."""
    result = new_result()
    key = os.environ.get(settings["api_key_env"], "").strip()
    if key == "":
        result["error"] = f"no API key: set the {settings['api_key_env']} environment variable (see README)"
        result["stop"] = True
        return result

    data, error, used, stop = get_json_with_retry(AIRLABS_URL, {"flight_iata": flight, "api_key": key})
    result["requests"] = used
    if data is None:
        result["error"] = error
        result["stop"] = stop
        return result
    if type(data) != dict:
        result["error"] = "unexpected answer shape"
        return result
    if "error" in data:
        problem = data["error"]
        message = "unknown error"
        if type(problem) == dict:
            message = str(problem.get("message", message))
        result["error"] = f"AirLabs: {message}"
        result["stop"] = "key" in message.lower()
        return result

    answer = data.get("response")
    if type(answer) == list:
        answer = pick_entry(answer)
    if type(answer) != dict:
        # Zero matches can mean "no flight today" or a changed API: report it, do not guess (W4).
        result["error"] = "no matching flight in the answer"
        return result
    result["record"] = make_record(answer)
    return result


# ---------- demo ----------

def load_demo(path):
    """Read demo_data.json and check its shape."""
    if not os.path.isfile(path):
        raise ValueError(f"demo file not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        try:
            scenario = json.load(handle)
        except ValueError:
            raise ValueError(f"demo file is not valid JSON: {path}")
    if type(scenario) != dict or type(scenario.get("flights")) != dict or type(scenario.get("steps")) != list:
        raise ValueError("demo file needs a 'flights' object and a 'steps' list")
    if len(scenario["steps"]) == 0:
        raise ValueError("demo file has no steps")
    for step in scenario["steps"]:
        if type(step) != dict or type(step.get("records")) != dict:
            raise ValueError("every demo step needs a 'records' object")
    return scenario


def fetch_demo(flight, settings, step):
    """Read the facts of one flight from one demo step; the last step repeats like a quiet day."""
    result = new_result()
    steps = load_demo(settings["demo_file"])["steps"]
    if type(step) != int or step < 0:
        step = 0
    if step >= len(steps):
        step = len(steps) - 1
    raw = steps[step]["records"].get(flight)
    if raw is None:
        result["error"] = f"{flight} is not in demo step {step + 1}"
    elif type(raw) != dict:
        result["error"] = "demo entry is not an object"
    elif "_error" in raw:
        result["error"] = f"{raw['_error']} (simulated)"
    else:
        result["record"] = make_record(raw)
    return result


# A dictionary picks the fetcher, like the ACTIONS dictionary in cli.py.
FETCHERS = {
    "demo": fetch_demo,
    "airlabs": fetch_airlabs,
}


def fetch_flight(settings, flight, step):
    """Get one flight from the source named in config.txt."""
    return FETCHERS[settings["source"]](flight, settings, step)
