"""Turn a raw answer (API or demo) into one flat flight record and validate it.

W4: "Validate means check each record against required fields, types and
allowed values before using it." Missing, empty and zero are different, so a
missing delay stays None and is never guessed as 0.
"""

STATUSES = ("scheduled", "active", "landed", "cancelled", "diverted", "incident", "unknown")

# record field -> field name in the AirLabs answer (demo_data.json uses the same names)
TEXT_FIELDS = {
    "flight": "flight_iata",
    "codeshare": "cs_flight_iata",
    "status": "status",
    "dep_iata": "dep_iata",
    "arr_iata": "arr_iata",
    "dep_time": "dep_time",
    "dep_estimated": "dep_estimated",
    "dep_gate": "dep_gate",
    "dep_terminal": "dep_terminal",
    "arr_gate": "arr_gate",
}
MINUTE_FIELDS = ("dep_delayed", "arr_delayed")
MIN_DELAY = -120       # a little early is fine
MAX_DELAY = 24 * 60    # more than a day late is treated as a broken value


def clean_text(value):
    """None and empty text both mean "not given"."""
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return text


def to_minutes(value):
    """Whole numbers become int, missing becomes None; anything else is kept so validation rejects it."""
    if value is None or value == "":
        return None
    if type(value) == int:
        return value
    if type(value) == float and value.is_integer():
        return int(value)
    if type(value) == str and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return value


def make_record(raw):
    """Copy the fields we use from a raw dictionary into a flat record."""
    record = {}
    for key in TEXT_FIELDS:
        record[key] = clean_text(raw.get(TEXT_FIELDS[key]))
    for key in ("flight", "codeshare"):
        if record[key] is not None:
            record[key] = record[key].upper()
    if record["status"] is not None:
        record["status"] = record["status"].lower()
    for key in MINUTE_FIELDS:
        record[key] = to_minutes(raw.get(key))
    return record


def validate_record(record, flight):
    """Return '' for a usable record, otherwise the reason it was rejected."""
    if record["flight"] is None:
        return "flight number missing"
    if record["flight"] != flight and record["codeshare"] != flight:
        return f"answer is about {record['flight']}, not {flight}"
    if record["status"] not in STATUSES:
        return f"unknown status '{record['status']}'"
    for key in MINUTE_FIELDS:
        value = record[key]
        if value is None:
            continue
        if type(value) != int:
            return f"{key} is not a number of minutes: '{value}'"
        if value < MIN_DELAY or value > MAX_DELAY:
            return f"{key} is out of range: {value}"
    return ""


def delay_of(record):
    """The larger of the departure and arrival delay; None when the source gave neither."""
    best = None
    for key in MINUTE_FIELDS:
        value = record.get(key)
        if type(value) == int and (best is None or value > best):
            best = value
    return best
