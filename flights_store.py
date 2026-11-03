"""Keep the watch list in flights.json: one entry per flight with an optional
own alert threshold and a note that is shown in the alert.

    {
      "TK1234": {"threshold_min": null, "note": "Pick up Ayse at ESB"},
      "PC2610": {"threshold_min": 20, "note": "Business trip"}
    }

threshold_min null means: use delay_threshold_min from config.txt.
"""

import json
import os

from storage import load_json, write_text_safely

MAX_NOTE_LENGTH = 80


# ---------- checks ----------

def normalize_flight(text):
    """Upper-case a flight number and drop spaces: ' tk 1234 ' -> 'TK1234'."""
    return text.replace(" ", "").strip().upper()


def check_flight(code):
    """Return why a flight number is not valid, or '' when it looks fine.

    IATA style: a 2-character airline code, 1-4 digits, optional letter (TK1234, PC2610, 3U8881).
    """
    if len(code) < 3 or len(code) > 7:
        return f"'{code}' must be 3-7 characters long, e.g. TK1234"
    if not (code.isascii() and code.isalnum()):
        return f"'{code}' may only contain letters A-Z and digits"
    if code[:2].isdigit():
        return f"'{code}' must start with a 2-character airline code such as TK"
    number = code[2:]
    if number[-1].isalpha():
        number = number[:-1]
    if not number.isdigit() or len(number) > 4:
        return f"'{code}' needs 1-4 digits after the airline code"
    return ""


def check_threshold(value):
    """Return why a threshold is not valid, or ''. None means "use the default"."""
    if value is None:
        return ""
    if type(value) != int or value < 1:
        return "threshold_min must be a whole number of at least 1 (or null for the default)"
    return ""


def clean_note(text):
    """A note is one short line of text."""
    if type(text) != str:
        return ""
    return text.replace("\n", " ").replace("\t", " ").strip()


# ---------- reading and writing ----------

def read_flights(path):
    """Return (flights, problems). flights keeps the file order: {code: {"threshold_min", "note"}}."""
    flights = {}
    problems = []
    data, warning = load_json(path, {})
    if warning != "":
        problems.append(warning)
    if type(data) != dict:
        problems.append("the file must contain one JSON object like {\"TK1234\": {...}}")
        return flights, problems

    for key in data:
        code = normalize_flight(str(key))
        entry = data[key]
        problem = check_flight(code)
        if problem == "" and type(entry) != dict:
            problem = f"{code}: the settings must be an object"
        if problem == "":
            problem = check_threshold(entry.get("threshold_min"))
            if problem != "":
                problem = f"{code}: {problem}"
        if problem == "" and code in flights:
            problem = f"{code} is listed twice"
        if problem != "":
            problems.append(f"{os.path.split(path)[1]}: {problem} (skipped)")
            continue
        flights[code] = {"threshold_min": entry.get("threshold_min"), "note": clean_note(entry.get("note", ""))}
    return flights, problems


def read_for_edit(path):
    """Read the list but refuse to edit a file with problems: saving would drop the bad entries."""
    flights, problems = read_flights(path)
    if len(problems) > 0:
        raise ValueError(f"fix the watch list first - {problems[0]}")
    return flights


def save_flights(path, flights):
    """Write the watch list as readable JSON."""
    write_text_safely(path, json.dumps(flights, indent=2, ensure_ascii=False) + "\n")


# ---------- editing ----------

def add_flight(path, text, threshold=None, note=""):
    """Add a flight or update its threshold/note. Return (code, status): added, updated or unchanged."""
    code = normalize_flight(text)
    problem = check_flight(code)
    if problem == "":
        problem = check_threshold(threshold)
    note = clean_note(note)
    if problem == "" and len(note) > MAX_NOTE_LENGTH:
        problem = f"the note may be at most {MAX_NOTE_LENGTH} characters"
    if problem != "":
        raise ValueError(problem)

    flights = read_for_edit(path)
    if code not in flights:
        flights[code] = {"threshold_min": threshold, "note": note}
        status = "added"
    elif threshold is None and note == "":
        return code, "unchanged"
    else:
        if threshold is not None:
            flights[code]["threshold_min"] = threshold
        if note != "":
            flights[code]["note"] = note
        status = "updated"
    save_flights(path, flights)
    return code, status


def remove_flight(path, text):
    """Remove one flight; return (code, removed)."""
    code = normalize_flight(text)
    flights = read_for_edit(path)
    if code not in flights:
        return code, False
    del flights[code]
    save_flights(path, flights)
    return code, True
