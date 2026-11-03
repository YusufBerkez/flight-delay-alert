"""Flight Delay Alert - watches flight numbers and pushes a notification on news.

News means a state change: a delay over the threshold, a growing delay, a
gate or schedule change, a departure, a cancellation. The same facts seen
again create no second alert.

Examples (run from the project folder):
    python cli.py demo
    python cli.py add --flight TK1234
    python cli.py check
    python cli.py watch --interval 300
    python cli.py menu
"""

import argparse

from dotenv import load_dotenv
load_dotenv()

from config_loader import DEFAULT_CONFIG_PATH, load_config
from flights_store import add_flight, remove_flight
from menu import run_menu
from monitor import check_with_lock, run_demo, show_status, watch


# ---------- actions ----------

def need_flight(args):
    """add/remove need --flight."""
    if args.flight is None:
        raise ValueError(f"{args.action} needs a flight number: add --flight TK1234")
    return args.flight


def run_check(args, settings):
    """One round over the watch list."""
    check_with_lock(settings, args.dry_run)


def run_watch(args, settings):
    """Rounds every --interval seconds until Ctrl+C (or --rounds N)."""
    interval = args.interval
    if interval is None:
        interval = settings["poll_interval_sec"]
    watch(settings, interval, args.rounds, args.dry_run)


def run_add(args, settings):
    """Put a flight on the watch list, or change its own threshold/note."""
    note = args.note
    if note is None:
        note = ""
    code, status = add_flight(settings["flights_file"], need_flight(args), args.threshold, note)
    if status == "added":
        print(f"Added {code} to the watch list.")
    elif status == "updated":
        print(f"Updated the settings of {code}.")
    else:
        print(f"{code} is already on the watch list (use --threshold or --note to change it).")


def run_remove(args, settings):
    """Take a flight off the watch list."""
    code, removed = remove_flight(settings["flights_file"], need_flight(args))
    if removed:
        print(f"Removed {code} from the watch list.")
    else:
        print(f"{code} is not on the watch list.")


def run_list(args, settings):
    """Show the watch list and the last saved status."""
    show_status(settings)


def run_demo_action(args, settings):
    """Play the demo scenario (no network, nothing saved)."""
    run_demo(settings)


def run_menu_action(args, settings):
    """Start the interactive menu."""
    run_menu(settings)


# A dictionary replaces an if/elif chain to pick the action (W3 S17).
ACTIONS = {
    "check": run_check,
    "watch": run_watch,
    "add": run_add,
    "remove": run_remove,
    "list": run_list,
    "demo": run_demo_action,
    "menu": run_menu_action,
}


# ---------- command-line interface ----------

def build_parser():
    """Create the argparse parser (W3 S28-31)."""
    parser = argparse.ArgumentParser(
        description="Watch flights and get a push notification when a delay, gate or schedule changes.",
    )
    parser.add_argument("action", choices=list(ACTIONS.keys()), help="what to do")
    parser.add_argument("--flight", help="add/remove: flight number such as TK1234")
    parser.add_argument("--threshold", type=int,
                        help="add: own alert threshold in minutes for this flight (default: config.txt)")
    parser.add_argument("--note", help='add: short note shown in the alert, e.g. "Pick up Ayse"')
    parser.add_argument("--interval", type=int,
                        help="watch: seconds between rounds (default: poll_interval_sec in config.txt)")
    parser.add_argument("--rounds", type=int, default=0,
                        help="watch: stop after N rounds (default 0 = until Ctrl+C)")
    parser.add_argument("--dry-run", action="store_true",
                        help="check/watch: print alerts but do not send them or save the state")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH,
                        help="settings file (default: config.txt)")
    return parser


def main():
    """Parse the arguments, run the chosen action and explain every error."""
    args = build_parser().parse_args()
    try:
        settings = load_config(args.config)
        ACTIONS[args.action](args, settings)
    except ValueError as error:
        print(f"Error: {error}")
    except OSError as error:
        print(f"Error: {error}")
    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    main()
