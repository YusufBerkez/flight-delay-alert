"""Monitoring rounds: fetch -> validate -> compare with saved state -> notify -> save.

Also holds the overlap lock and the watch loop (W4: scheduling, overlap and
missed-run policy).
"""

import json
import os
import time
from datetime import datetime, timezone

from detector import find_changes, keep_known_values
from flights_store import check_threshold, clean_note, read_flights
from notifier import deliver, send_alert
from records import delay_of, validate_record
from sources import fetch_flight, load_demo
from storage import load_json, now_utc, write_text_safely

FAILS_BEFORE_ALERT = 3
LOCK_NAME = ".flight_alert.lock"
LOCK_STALE_SEC = 600
MIN_REAL_INTERVAL_SEC = 30


# ---------- saved state ----------

def empty_state():
    """flights: last facts per flight; quota: API calls this month; demo_step: next demo step."""
    return {"flights": {}, "quota": {"month": "", "used": 0}, "demo_step": 0}


def load_state(path):
    """Return (state, warning); a wrong shape starts empty instead of crashing later."""
    state, warning = load_json(path, None)
    if state is None:
        return empty_state(), warning
    if type(state) != dict or type(state.get("flights")) != dict:
        return empty_state(), "state file has an unexpected shape; starting empty"
    if type(state.get("quota")) != dict:
        state["quota"] = {"month": "", "used": 0}
    if type(state.get("demo_step")) != int or state["demo_step"] < 0:
        state["demo_step"] = 0
    return state, warning


def save_state(path, state):
    """Save the state as readable JSON (W4: "A JSON file keeps the last result even when Python stops")."""
    write_text_safely(path, json.dumps(state, indent=2, ensure_ascii=False))


def get_entry(state, flight):
    """The saved entry of one flight, repaired if a field is missing or has the wrong type."""
    saved = state["flights"].get(flight)
    if type(saved) != dict:
        saved = {}
    entry = {"record": None, "notified_delay": None, "fail_count": 0, "checked_at": None}
    for key in entry:
        if key in saved:
            entry[key] = saved[key]
    if type(entry["record"]) != dict:
        entry["record"] = None
    if type(entry["fail_count"]) != int:
        entry["fail_count"] = 0
    if type(entry["notified_delay"]) != int:
        entry["notified_delay"] = None
    return entry


def requests_left(state, limit):
    """API calls still allowed this month; the counter restarts every month."""
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    quota = state["quota"]
    if quota.get("month") != month or type(quota.get("used")) != int:
        state["quota"] = {"month": month, "used": 0}
    return limit - state["quota"]["used"]


# ---------- one round ----------

def handle_failure(settings, flight, entry, error, dry_run):
    """Count failures in a row; after FAILS_BEFORE_ALERT, warn once that alerts may be missed."""
    entry["fail_count"] += 1
    print(f"  {flight}: source problem - {error} ({entry['fail_count']} in a row)")
    if entry["fail_count"] == FAILS_BEFORE_ALERT:
        body = (f"No usable answer {FAILS_BEFORE_ALERT} times in a row.\n"
                f"Last error: {error}\nChanges of this flight may be missed until the source is back.")
        send_alert(settings, flight, f"{flight}: source not answering", body, 4, dry_run)


def describe(record):
    """One status line for the console."""
    delay = delay_of(record)
    if record["status"] in ("cancelled", "diverted"):
        delay_text = "no delay shown"
    elif delay is None:
        delay_text = "delay unknown"
    else:
        delay_text = f"{delay} min late"
    return f"{record['status']}, {delay_text}, gate {record['dep_gate']}"


def threshold_for(settings, watch_entry):
    """A flight's own threshold_min, or the default from config.txt."""
    if watch_entry["threshold_min"] is None:
        return settings["delay_threshold_min"]
    return watch_entry["threshold_min"]


def run_round(settings, flights, state, dry_run=False):
    """Check every flight of the watch list ({code: {"threshold_min", "note"}}) once and return counts.

    The saved record changes only after the news was delivered, so a failed
    notification is tried again next round (W4: "Save valid state; keep errors separate").
    """
    counts = {"checked": 0, "alerts": 0, "errors": 0, "rejected": 0}
    for flight in flights:
        if settings["source"] != "demo" and requests_left(state, settings["max_requests_per_month"]) <= 0:
            print("Monthly request budget is used up - the remaining flights are skipped.")
            counts["errors"] += 1
            break

        entry = get_entry(state, flight)
        result = fetch_flight(settings, flight, state["demo_step"])
        if result["requests"] > 0:
            state["quota"]["used"] += result["requests"]

        if result["error"] != "":
            counts["errors"] += 1
            if result["stop"]:
                # A missing or wrong key is a setup problem, not an outage (W4: stop on refusal).
                print(f"  {flight}: {result['error']}")
                print("Stopping this round: fix the problem above first.")
                break
            handle_failure(settings, flight, entry, result["error"], dry_run)
            state["flights"][flight] = entry
            continue

        problem = validate_record(result["record"], flight)
        if problem != "":
            counts["rejected"] += 1
            print(f"  {flight}: record rejected - {problem} (saved state kept)")
            continue

        if entry["fail_count"] >= FAILS_BEFORE_ALERT:
            send_alert(settings, flight, f"{flight}: source is back",
                       f"The source answers again after {entry['fail_count']} failures.", 2, dry_run)
        entry["fail_count"] = 0

        record = keep_known_values(entry["record"], result["record"])
        changes, notified = find_changes(entry["record"], record, entry["notified_delay"],
                                         threshold_for(settings, flights[flight]), settings["delay_step_min"])
        print(f"  {flight}: {describe(record)} - {len(changes)} change(s)")
        delivered = True
        if len(changes) > 0:
            counts["alerts"] += 1
            # The evidence is what the source really sent, not the remembered values.
            delivered = deliver(settings, changes, result["record"], flights[flight]["note"], dry_run)
        if delivered:
            entry["record"] = record
            entry["notified_delay"] = notified
            entry["checked_at"] = now_utc()
        else:
            print(f"  {flight}: alert not delivered - state kept, it will be tried again next round")
        state["flights"][flight] = entry
        counts["checked"] += 1
    return counts


def load_watch_list(settings):
    """Read flights.json and print its problems."""
    flights, problems = read_flights(settings["flights_file"])
    for problem in problems:
        print(f"Warning: {problem}")
    return flights


def check_once(settings, dry_run=False):
    """One complete round: load state, check all flights, save state."""
    flights = load_watch_list(settings)
    if len(flights) == 0:
        print("The watch list is empty. Add a flight: python cli.py add --flight TK1234")
        return
    state, warning = load_state(settings["state_file"])
    if warning != "":
        print(f"Warning: {warning}")
    for name in list(state["flights"].keys()):
        if name not in flights:
            del state["flights"][name]  # removed from the watch list

    print(f"Checking {len(flights)} flight(s), source '{settings['source']}', {now_utc()}")
    counts = run_round(settings, flights, state, dry_run)
    if settings["source"] == "demo":
        state["demo_step"] += 1
    if dry_run:
        print("Dry run: the state file was not changed.")
    else:
        save_state(settings["state_file"], state)
    print(f"Summary: {counts['checked']} checked, {counts['alerts']} with news, "
          f"{counts['errors']} source errors, {counts['rejected']} rejected records")


# ---------- overlap lock ----------

def lock_path(settings):
    """The lock file sits next to the state file."""
    return os.path.join(os.path.dirname(settings["state_file"]), LOCK_NAME)


def acquire_lock(path, stale_after_sec):
    """Refuse to start while another fresh run holds the lock (W4: overlap can corrupt a scan)."""
    if os.path.exists(path):
        age = time.time() - os.path.getmtime(path)
        if age < stale_after_sec:
            raise ValueError(f"another check is running (lock is {int(age)} s old). "
                             f"If it crashed, delete {path}")
        print(f"Removing an old lock left by a stopped run ({int(age)} s old).")
        os.remove(path)
    try:
        with open(path, "x", encoding="utf-8") as handle:  # "x" fails if the file already exists
            handle.write(now_utc())
    except FileExistsError:
        raise ValueError("another check started at the same moment - try again")


def refresh_lock(path):
    """Show that the long-running watch loop is still alive."""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(now_utc())


def release_lock(path):
    """Remove the lock when the run ends, also after an error."""
    if os.path.exists(path):
        os.remove(path)


def check_with_lock(settings, dry_run=False):
    """check_once protected by the lock (used by `check` and the menu)."""
    path = lock_path(settings)
    acquire_lock(path, LOCK_STALE_SEC)
    try:
        check_once(settings, dry_run)
    finally:
        release_lock(path)


# ---------- watch loop ----------

def print_budget_hint(settings, flights_count, interval):
    """Show how long the monthly API budget lasts at this interval."""
    if settings["source"] == "demo" or flights_count == 0:
        return
    state, warning = load_state(settings["state_file"])
    left = requests_left(state, settings["max_requests_per_month"])
    per_day = flights_count * (86400 // interval)
    print(f"Request budget: {left} left this month; this interval needs about {per_day} per day "
          f"(enough for about {left // per_day} day(s)).")


def watch(settings, interval, rounds, dry_run=False):
    """Repeat check_once every `interval` seconds; rounds=0 means until Ctrl+C.

    Missed-run policy (W4): if the computer slept, the loop simply runs one
    fresh round. This is a current-state monitor, and the saved state makes
    sure a change that happened in between is still reported.
    """
    if interval < 1:
        raise ValueError("--interval must be at least 1 second")
    if settings["source"] != "demo" and interval < MIN_REAL_INTERVAL_SEC:
        raise ValueError(f"with a real source --interval must be at least {MIN_REAL_INTERVAL_SEC} s")
    if rounds < 0:
        raise ValueError("--rounds cannot be negative")

    print_budget_hint(settings, len(load_watch_list(settings)), interval)
    path = lock_path(settings)
    acquire_lock(path, max(LOCK_STALE_SEC, interval * 3))
    try:
        done = 0
        while rounds == 0 or done < rounds:
            done += 1
            print(f"\n=== Round {done} ===")
            started = time.perf_counter()  # W4: a monotonic clock for durations
            check_once(settings, dry_run)
            refresh_lock(path)
            if rounds != 0 and done >= rounds:
                break
            wait = interval - (time.perf_counter() - started)
            if wait > 0:
                print(f"Next round in {wait:.0f} s (Ctrl+C stops)")
                time.sleep(wait)
    finally:
        release_lock(path)


# ---------- status and demo ----------

def show_status(settings):
    """Print the watch list with the last saved facts and the API budget."""
    flights = load_watch_list(settings)
    state, warning = load_state(settings["state_file"])
    if warning != "":
        print(f"Warning: {warning}")
    topic = settings["ntfy_topic"]
    if topic == "":
        topic = "(not set - alerts are only printed)"
    print(f"Source: {settings['source']}   threshold: {settings['delay_threshold_min']} min   ntfy topic: {topic}")
    if settings["source"] != "demo":
        left = requests_left(state, settings["max_requests_per_month"])
        print(f"API requests left this month: {left} of {settings['max_requests_per_month']}")
    if len(flights) == 0:
        print("The watch list is empty.")
        return
    for flight in flights:
        entry = get_entry(state, flight)
        settings_text = f"threshold {threshold_for(settings, flights[flight])} min"
        if flights[flight]["note"] != "":
            settings_text += f", note: {flights[flight]['note']}"
        if entry["record"] is None:
            print(f"  {flight} ({settings_text}): not checked yet")
        else:
            print(f"  {flight} ({settings_text}): {describe(entry['record'])} (checked {entry['checked_at']})")


def run_demo(settings):
    """Play every step of demo_data.json in memory: nothing is sent and no file changes."""
    scenario = load_demo(settings["demo_file"])
    demo_settings = dict(settings)
    demo_settings["source"] = "demo"

    flights = {}
    for code in scenario["flights"]:
        given = scenario["flights"][code]
        if type(given) != dict or check_threshold(given.get("threshold_min")) != "":
            raise ValueError(f"demo file: bad settings for {code}")
        flights[code] = {"threshold_min": given.get("threshold_min"), "note": clean_note(given.get("note", ""))}

    state = empty_state()
    steps = scenario["steps"]
    for index in range(len(steps)):
        print(f"\n--- Demo step {index + 1}/{len(steps)}: {steps[index].get('label', '')} ---")
        state["demo_step"] = index
        run_round(demo_settings, flights, state, dry_run=True)
    print("\nDemo finished: nothing was sent and no file was changed.")
