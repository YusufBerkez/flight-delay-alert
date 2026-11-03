# Contribution – Yusuf Berke Zengin

- **Student ID:** 2409111002
- **GitHub:** YusufBerkez
- **Role:** Monitoring loop, interfaces, documentation and merges
- **Branch / Pull Request:** `main` (first commit, creates the repository) · merges of the other branches

## Files I wrote
- `.gitignore`
- `monitor.py`
- `menu.py`
- `cli.py`
- `README.md`
- `contributions/YUSUF_BERKE_ZENGIN_OGRENCINO_GITHUBADI.md`

## What I implemented
- `run_round()`: fetch -> validate -> compare -> notify -> save for every flight; the saved record changes only after the alert was delivered.
- Monthly request budget (`requests_left`), counted per HTTP try and reset every month; `watch` prints how many days the budget lasts.
- Overlap lock `.flight_alert.lock` created with mode `"x"`, removed in `finally`, replaced when older than 10 minutes.
- Source health: after 3 failures in a row one "source not answering" alert, and "source is back" when it answers again.
- `watch` loop with `time.perf_counter()` for durations and a documented missed-run policy.
- Two interfaces: `cli.py` (argparse with `choices`, `type=int`, `store_true`, `ACTIONS` dictionary) and `menu.py` (input() validation loops).
- README with usage, configuration, the W4 mapping table and known limits; repository setup and the merges.

## Design decisions
- A failed notification keeps the old state, so the news is tried again next round instead of being lost.
- A missing or wrong API key stops the round and does not count as a source outage.
- Missed runs: one fresh round is enough for a current-state monitor; the saved state still reports what changed in between.

## Course topics I applied
- Scheduling, overlap and missed-run policy (W4)
- A monotonic clock for durations (W4)
- Save valid state; restart from stored evidence (W4)
- argparse, dispatch dictionary, input() validation loop, main() guard (W3)

## Commit
1. Add monitoring loop, command-line interface, menu and README
