# Contribution – Ömer Ali Taylan

- **Student ID:** 2409111077
- **GitHub:** omeralitaylan
- **Role:** Settings and watch list
- **Branch / Pull Request:** `feature/config`

## Files I wrote
- `config.txt`
- `config_loader.py`
- `flights_store.py`
- `flights.json`
- `contributions/OMER_ALI_TAYLAN_2409111077_omeralitaylan.md`

## What I implemented
- `config.txt`: plain `key = value` settings (source, ntfy topic, thresholds, request budget, file names) that anyone can edit in Notepad.
- `load_config()` reads the file line by line and stops with the line number on an unknown key, a missing `=`, a bad number or a value under its minimum (for example `poll_interval_sec` under 30).
- `check_topic()` allows only letters, digits, `-` and `_` in the ntfy topic, because the topic becomes part of a URL.
- `flights_store.py` keeps the watch list in `flights.json`: every flight can have its own `threshold_min` and a `note` that is shown in the alert.
- `check_flight()` validates IATA flight numbers with string methods only (`isalnum`, `isdigit`, slicing): `TK1234` is fine, `12345` and `XX` are refused.
- `read_for_edit()` refuses to edit a watch list that has broken entries, so saving can never silently drop an entry.

## Design decisions
- The API key is not a setting: `config.txt` only stores the *name* of the environment variable, so the key never reaches the file or Git (W4: protect tokens).
- `threshold_min: null` means "use the default", so missing is not the same as zero (W4: missing, empty and zero are different).
- We discussed SQLite for the watch list but kept JSON: databases are a later course topic and a few flight numbers do not need a database.

## Course topics I applied
- `with open` and reading a file line by line (W2, W3)
- String methods `strip`, `split`, `startswith`, `isdigit`, `isalnum`, `upper` (W3)
- Dictionaries and `.get()` (W3)
- `json.load` / `json.dumps` for structured data (W4)
- Validate before trusting: required fields, types, allowed values (W4)
- Protect tokens: keep secrets out of files and Git (W4)

## Commit
1. Add settings file, config loader and flight watch list
