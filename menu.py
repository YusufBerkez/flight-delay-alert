"""Interactive menu: a second interface next to the command line.

Every answer is checked in an input() loop (W3: input validation), so a
wrong key never crashes the program.
"""

from flights_store import MAX_NOTE_LENGTH, add_flight, check_flight, normalize_flight, read_flights, remove_flight
from monitor import check_with_lock, run_demo, show_status

MENU_TEXT = """
==== Flight Delay Alert ====
  1  Add a flight
  2  Remove a flight
  3  Show watch list and last status
  4  Check all flights now
  5  Play the demo scenario
  0  Quit"""


def ask(question):
    """input() that treats end of input (Ctrl+Z / Ctrl+D) as "quit"."""
    try:
        return input(question).strip()
    except EOFError:
        return None


def ask_flight():
    """Ask until the flight number is valid; None when the user goes back."""
    while True:
        text = ask("Flight number (e.g. TK1234, empty = back): ")
        if text is None or text == "":
            return None
        code = normalize_flight(text)
        problem = check_flight(code)
        if problem == "":
            return code
        print(f"Not valid: {problem}")


def ask_threshold(default):
    """Ask until the answer is empty (use the default) or a whole number of at least 1."""
    while True:
        text = ask(f"Own alert threshold in minutes (empty = default {default}): ")
        if text is None or text == "":
            return None
        if text.isdigit() and int(text) >= 1:
            return int(text)
        print("Please type a whole number of at least 1, or press Enter.")


def ask_note():
    """Ask until the note is short enough (empty is fine)."""
    while True:
        text = ask(f"Note shown in the alert (max {MAX_NOTE_LENGTH} characters, empty = none): ")
        if text is None:
            return ""
        if len(text) <= MAX_NOTE_LENGTH:
            return text
        print(f"That note has {len(text)} characters; please keep it to {MAX_NOTE_LENGTH}.")


def menu_add(settings):
    """Add a flight with its own threshold and note, or update them."""
    code = ask_flight()
    if code is None:
        return
    threshold = ask_threshold(settings["delay_threshold_min"])
    note = ask_note()
    code, status = add_flight(settings["flights_file"], code, threshold, note)
    if status == "added":
        print(f"Added {code}.")
    elif status == "updated":
        print(f"Updated {code}.")
    else:
        print(f"{code} is already on the list.")


def menu_remove(settings):
    """Show the list and remove the chosen flight."""
    flights, problems = read_flights(settings["flights_file"])
    if len(flights) == 0:
        print("The watch list is empty.")
        return
    print("Watching: " + ", ".join(flights))
    text = ask("Flight to remove (empty = back): ")
    if text is None or text == "":
        return
    code, removed = remove_flight(settings["flights_file"], text)
    if removed:
        print(f"Removed {code}.")
    else:
        print(f"{code} is not on the list.")


def menu_status(settings):
    show_status(settings)


def menu_check(settings):
    check_with_lock(settings)


def menu_demo(settings):
    run_demo(settings)


MENU_ACTIONS = {
    "1": menu_add,
    "2": menu_remove,
    "3": menu_status,
    "4": menu_check,
    "5": menu_demo,
}


def run_menu(settings):
    """Show the menu until the user chooses 0 or input ends."""
    while True:
        print(MENU_TEXT)
        choice = ask("Choice: ")
        if choice is None or choice == "0":
            print("Bye.")
            return
        action = MENU_ACTIONS.get(choice)
        if action is None:
            print("Please type one of the numbers 0-5.")
            continue
        try:
            action(settings)
        except ValueError as error:
            print(f"Error: {error}")
        except OSError as error:
            print(f"Error: {error}")
