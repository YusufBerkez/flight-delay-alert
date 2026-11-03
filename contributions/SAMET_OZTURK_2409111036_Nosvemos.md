# Contribution – Samet Öztürk

- **Student ID:** 2409111036
- **GitHub:** Nosvemos
- **Role:** Validation and change detection
- **Branch / Pull Request:** `feature/detector` → https://github.com/YusufBerkez/flight-delay-alert/pull/4

## Files I wrote
- `records.py`
- `detector.py`
- `contributions/SAMET_OZTURK_2409111036_Nosvemos.md`

## What I implemented
- `make_record()` copies only the fields we use from a raw answer into one flat record and cleans them (`None` and empty text both mean "not given").
- `to_minutes()` turns whole numbers into `int`, keeps a missing value as `None` and keeps anything else unchanged, so validation rejects it instead of guessing.
- `validate_record()` checks the flight number (also codeshares), the allowed statuses and the delay type and range; a delay of `"about an hour"` is rejected.
- `find_changes()` compares the saved and the new record and reports: delay over the threshold, delay grew by the step, back under the threshold, gate change, schedule change, departure, cancellation, diversion.
- `notified_delay` remembers the delay of the last alert, so a slowly growing delay (20 -> 30 -> 40) is still reported once it adds up.
- `keep_known_values()`: a field that disappears from the answer keeps its last known value, so it does not create a fake change.

## Design decisions
- The same facts seen twice create no second alert (W4: notify on a state change, not on repeated observations).
- Every change has a priority (cancelled 5 ... departed 2) that becomes the ntfy priority.

## Course topics I applied
- Validate before trusting: required fields, types, allowed values (W4)
- Missing, empty and zero are different; do not guess zero (W4)
- Use a stable id and compare relevant fields (W4)
- State changes create events (W4)
- Dictionaries, tuples as return values, `if/elif` (W3)

## Commit
1. Add record validation and change detection
