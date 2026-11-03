# Flight Delay Alert

A monitor that watches a list of flight numbers through a flight-data **API** and sends a **push notification to your phone** only when something new happens: a delay over your threshold, a growing delay, a gate change, a new departure time, a departure or a cancellation.

COE203 Advanced Programming with Python · Project 2 (web monitoring: API + scheduling + notifications)

## The problem

Airport screens and airline apps show the _current_ state, but nobody tells you the moment it changes. Travellers, drivers who pick people up and small travel agencies keep refreshing pages. Simple alert scripts make it worse: they either notify on every check ("still delayed", "still delayed") or silently stop when the API fails.

Flight Delay Alert:

1. **Reads facts from an API** (AirLabs) or from a demo file, with timeouts and a retry budget.
2. **Validates every record** before trusting it (a delay of `"about an hour"` is rejected, not guessed).
3. **Compares with the saved state** and turns only real changes into alerts.
4. **Sends the alert with ntfy**, with the raw evidence kept separate from the interpretation.
5. **Protects itself**: monthly request budget, overlap lock, safe state file, warning when the source stops answering.

```
flights.json ─► sources.py ──► records.py ──► detector.py ──► notifier.py ──► phone (ntfy)
 (watch list)   (API / demo)   (validate)     (old vs new)    (alert + log)
                                   ▲               │
                                   └── state.json ◄┘  (saved only after delivery)
```

## Requirements

- Python 3.8 or newer
- `requests`
- `python-dotenv`

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

## Quick start

### 1. Create a virtual environment

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Run the project

Run every command **from the project folder** (where `config.txt` is). The default source is `demo`, so this works without an API key or internet connection.

```bash
python cli.py demo                 # play the 10-step demo scenario (nothing is sent or saved)
python cli.py check                # one round over flights.json (demo source walks one step per run)
python cli.py list                 # watch list + last saved status
python cli.py add --flight TK2002 --threshold 30 --note "Pick up Mert"
python cli.py menu                 # interactive menu (second interface)
```

## Usage

```
python cli.py ACTION [options]
```

| Action   | What it does                                                                                                                                                                       | Options                                                                                                                   |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `demo`   | Plays every step of `demo_data.json` in memory: delay, gate change, growing delay, same facts (no alert), broken record, three source failures, cancellation, recovery, departure. | –                                                                                                                         |
| `check`  | One round: fetch, validate, compare, notify, save.                                                                                                                                 | `--dry-run` print alerts, send nothing, save nothing                                                                      |
| `watch`  | Repeats `check` every N seconds until Ctrl+C. Prints how long the monthly API budget lasts.                                                                                        | `--interval SEC` (default `poll_interval_sec`, min 30 with a real source) · `--rounds N` · `--dry-run`                    |
| `add`    | Put a flight on the watch list in `flights.json`, or change its settings. Flight numbers are checked (`TK1234`, `PC2610`, `3U8881`).                                               | `--flight CODE` (required) · `--threshold MIN` own alert threshold · `--note TEXT` shown in the alert (max 80 characters) |
| `remove` | Take a flight off the watch list.                                                                                                                                                  | `--flight CODE` (required)                                                                                                |
| `list`   | Shows the watch list, the last saved facts and the API requests left this month.                                                                                                   | –                                                                                                                         |
| `menu`   | Interactive menu with the same functions; every answer is validated.                                                                                                               | –                                                                                                                         |

All actions accept `--config FILE`. `python cli.py --help` shows the built-in help.

## Watch list (`flights.json`)

```json
{
  "TK1234": { "threshold_min": null, "note": "Pick up Ayse at ESB" },
  "PC2610": { "threshold_min": 20, "note": "Business trip to Izmir" }
}
```

`threshold_min: null` uses `delay_threshold_min` from `config.txt`. The note is printed in every alert of that flight. Edit it with `add`/`remove`, the menu, or any text editor; a broken entry is skipped with a warning, and the program refuses to edit the file until it is fixed (so no entry is lost).

## Configuration (`config.txt`)

Plain `key = value` lines, `#` starts a comment. Unknown keys and bad numbers stop the program with the line number.

| Key                                                   | Meaning                                                                                 | Default                  |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------ |
| `source`                                              | `demo` or `airlabs`                                                                     | `demo`                   |
| `api_key_env`                                         | name of the environment variable that holds the AirLabs key                             | `AIRLABS_API_KEY`        |
| `ntfy_server`, `ntfy_topic`                           | where alerts go; empty topic = only print                                               | `https://ntfy.sh`, empty |
| `ntfy_token_env`                                      | environment variable with an ntfy access token (optional)                               | `NTFY_TOKEN`             |
| `delay_threshold_min`                                 | alert when a flight is at least this late (a flight in `flights.json` can have its own) | `15`                     |
| `delay_step_min`                                      | alert again each time the delay grows this much more                                    | `15`                     |
| `poll_interval_sec`                                   | seconds between `watch` rounds                                                          | `300`                    |
| `max_requests_per_month`                              | stop calling the API at this count (set it below your plan's limit)                     | `900`                    |
| `flights_file`, `state_file`, `log_file`, `demo_file` | file names, relative to `config.txt`                                                    |                          |

## Real data and phone notifications

**Flight data (AirLabs).** Create a free key on `airlabs.co`, then create a `.env` file in the project folder and write your key inside it:

```env
AIRLABS_API_KEY=your-key
```

The application loads this file automatically via `python-dotenv`. The `.env` file is listed in `.gitignore` and must never be pushed to GitHub.

Alternatively, you can set the key in Windows PowerShell:

```powershell
$env:AIRLABS_API_KEY = "your-key"      # PowerShell, this window only
```

Then set `source = airlabs` in `config.txt` and set `max_requests_per_month` a little below the monthly limit of your API plan.

**Notifications (ntfy).** Install the ntfy app, subscribe to a topic with a hard-to-guess name and write that name into `ntfy_topic`. Anyone who knows a public topic name can read it; for a protected topic put the token into the `NTFY_TOKEN` environment variable and it is sent as `Authorization: Bearer ...`.

**Running it regularly.** Either keep `python cli.py watch` open, or let Windows Task Scheduler start `python cli.py check` every few minutes. The lock file stops two runs from overlapping.

## How the design follows the Week 4 lecture

| Lecture idea (W4)                                                                   | Where                                                                                                       |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Set timeouts; check the status code                                                 | `sources.get_json_with_retry`, `notifier.send_ntfy`                                                         |
| Retry a limited number of times with backoff (1 s, 2 s); wait as `Retry-After` says | `sources.get_json_with_retry`                                                                               |
| If access is denied, stop and resolve it                                            | 401/403/unknown key stop the round (`stop` flag)                                                            |
| Only repeat an operation when repeating its effect is acceptable                    | GET is retried; the ntfy POST is not (it could send twice); the state is kept so the next round tries again |
| Validate each record: required fields, types, allowed values                        | `records.validate_record`                                                                                   |
| Missing, empty and zero are different; do not guess zero                            | a missing delay stays `None`; `records.to_minutes`                                                          |
| Use a stable id; compare relevant fields                                            | flight number is the key; `detector.find_changes`                                                           |
| Notify on state change, not on repeated observations                                | `detector.find_changes` + `notified_delay`                                                                  |
| Save valid state; do not replace valid state with empty data                        | state saved only after delivery; rejected records keep the old state                                        |
| Protect state                                                                       | `storage.write_text_safely` (temp file + `.bak`), broken file kept as `.broken`                             |
| Keep evidence separate from interpretation                                          | alert text: what changed, then `Evidence:` with the raw source values                                       |
| Zero matches can mean a broken extractor                                            | "no matching flight in the answer" is reported as a source problem, three in a row send a warning           |
| Overlap can corrupt a scan                                                          | `monitor.acquire_lock` (`.flight_alert.lock`, stale after 10 min)                                           |
| Missed runs need a policy                                                           | one fresh round after a gap; the saved state still reports what changed in between                          |
| Aware datetimes; a monotonic clock for durations                                    | `storage.now_utc` (UTC offset), `time.perf_counter` in `watch`                                              |
| Load tokens securely; exclude them from logs and Git                                | keys from environment variables, error messages show only the error type, `.gitignore`                      |

From Week 3: `argparse` with `choices`/`type=int`/`store_true`, the `ACTIONS` dictionary instead of `if/elif`, `input()` validation loops in the menu, `main()` with the `__main__` guard, f-strings.

## Project files

| File               | Purpose                                                                             |
| ------------------ | ----------------------------------------------------------------------------------- |
| `cli.py`           | Command-line interface: parses arguments and runs the action                        |
| `menu.py`          | Interactive menu (second interface)                                                 |
| `monitor.py`       | One monitoring round, saved state, request budget, lock, watch loop, status, demo   |
| `sources.py`       | Fetchers for `airlabs` and `demo`, HTTP retries                                     |
| `records.py`       | Raw answer → flat record, validation, `delay_of`                                    |
| `detector.py`      | Old vs new record → list of changes with priorities                                 |
| `notifier.py`      | Alert text, ntfy delivery, `alerts_log.txt`                                         |
| `storage.py`       | Safe writing and reading of JSON/text files, UTC timestamps                         |
| `flights_store.py` | Reads and edits `flights.json`, checks flight numbers, thresholds and notes         |
| `config_loader.py` | Reads and checks `config.txt`                                                       |
| `config.txt`       | Settings                                                                            |
| `flights.json`     | Watch list: every flight with its own `threshold_min` (`null` = default) and `note` |
| `demo_data.json`   | Demo scenario in AirLabs field names                                                |
| `contributions/`   | One file per team member                                                            |

Created while running (ignored by Git): `state.json` (+ `.bak`, `.broken`), `alerts_log.txt`, `.flight_alert.lock`.

## Known limits

- The AirLabs adapter uses the documented field names (`flight_iata`, `dep_delayed`, `dep_gate`, …). A valid API key and a real flight record (TK2524) were successfully tested; however, AirLabs may not return every requested flight.
- The free plan's monthly limit decides how many flights and how short an interval are possible; `watch` prints the estimate.
- Delays are the larger of departure and arrival delay as reported by the source; the program does not calculate delays itself.

## Team

| Member             | Part                                      | Files                                                                |
| ------------------ | ----------------------------------------- | -------------------------------------------------------------------- |
| Ömer Ali Taylan    | Settings and watch list                   | `config.txt`, `config_loader.py`, `flights_store.py`, `flights.json` |
| Zehra Nur Ak       | Data sources and demo scenario            | `sources.py`, `demo_data.json`                                       |
| Samet Öztürk       | Validation and change detection           | `records.py`, `detector.py`                                          |
| Elif Aktaş         | Safe storage and notifications            | `storage.py`, `notifier.py`                                          |
| Yusuf Berke Zengin | Monitoring loop, interfaces, docs, merges | `monitor.py`, `menu.py`, `cli.py`, `README.md`, `.gitignore`         |

Each member describes their own work in `contributions/`.
