# Contribution – Elif Aktaş

- **Student ID:** [2409011009]
- **GitHub:** [aelif-aktas]
- **Role:** Safe storage and notifications
- **Branch / Pull Request:** `feature/storage-notify` 

## Files I wrote
- `storage.py`
- `notifier.py`
- `contributions/ELIF_AKTAS_2409011009_aelif-aktas.md`

## What I implemented
- `write_text_safely()` writes to a temporary file, keeps the old file as `.bak` and only then moves the new file into place, so a crash never leaves a half-written state.
- `load_json()` falls back to the `.bak` copy when the file is broken and keeps the broken file as `.broken` evidence.
- `now_utc()` gives aware UTC timestamps (`+00:00`).
- `build_message()` puts what changed first, then a separate `Evidence:` block with the raw values from the source, plus the flight's note.
- `send_ntfy()` uses `requests.post(url, data=body.encode("utf-8"), headers=...)` with an optional `Authorization: Bearer` token from an environment variable and a 10 s timeout.
- `send_alert()` prints, sends and appends one line per alert to `alerts_log.txt`; it reports whether the alert counts as delivered.

## Design decisions
- The ntfy POST is not retried: repeating it could send the alert twice. Instead the monitor keeps the old state, so the next round tries again.
- With an empty `ntfy_topic` alerts are only printed, so nobody sends a notification by accident while testing.

## Course topics I applied
- Protect state; do not replace valid state with empty data (W4)
- Keep evidence separate from interpretation (W4)
- `requests.post` with a Bearer token and a timeout (W4: ntfy fragment)
- Aware datetimes (W4), `shutil.copy` / `shutil.move` (W3)
- File modes `w` and `a` (W2/W3)

## Commit
1. Add safe state storage and ntfy notifier
