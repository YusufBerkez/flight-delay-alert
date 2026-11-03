# Contribution – Zehra Nur Ak

- **Student ID:** 2409111031
- **GitHub:** zehranurak
- **Role:** Data sources and demo scenario
- **Branch / Pull Request:** `feature/sources` → PR will be linked after it is created

## Files I wrote
- `sources.py`
- `demo_data.json`
- `contributions/ZEHRA_NUR_AK_OGRENCINO_GITHUBADI.md`

## What I implemented
- `get_json_with_retry()`: `requests.get` with a 10 s timeout and a retry budget of 3 tries (wait 1 s, then 2 s) for timeouts, network errors and 5xx.
- HTTP 429 waits as `Retry-After` says (up to 60 s); 401/403 and an unknown API key stop the round instead of retrying.
- `fetch_airlabs()` reads the key from an environment variable and never prints it: error messages contain only the error type, because a full message could contain the URL with the key.
- AirLabs answers HTTP 200 with an `error` object for a wrong key; I checked this with a wrong key and handle it.
- `fetch_demo()` reads `demo_data.json`, one step per round, and can simulate source failures with `_error`.
- `FETCHERS` dictionary picks the fetcher from the `source` setting, so the rest of the program does not care where the data comes from.

## Design decisions
- A GET can be repeated safely, so it is retried. "No matching flight" is reported as a source problem, not as "no news" (W4: zero matches can mean a broken extractor).
- The demo file uses the same field names as AirLabs, so the demo goes through exactly the same code as real data.

## Course topics I applied
- `requests.get` with `params` and `timeout`, checking `status_code` (W4)
- Retry with a limit and backoff; wait as Retry-After says (W4)
- If access is denied, stop and resolve it (W4)
- `try/except` with specific exceptions (W3)
- `json.load` (W4), dictionaries as a dispatch table (W3)

## Commit
1. Add AirLabs and demo data sources with retries
