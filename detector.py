"""Compare the saved record of a flight with the new one and list the news.

W4: "Notify when a useful change occurs; seeing the same open item again adds
no news." The same delay seen twice therefore creates no second alert.
"""

from records import delay_of

PRIORITY = {
    "cancelled": 5,
    "diverted": 5,
    "delay": 4,
    "delay_up": 4,
    "gate": 3,
    "time": 3,
    "departed": 2,
    "delay_over": 2,
}

# Fields that keep their last known value when the source stops sending them.
REMEMBERED_FIELDS = ("dep_gate", "dep_terminal", "arr_gate", "dep_time", "dep_estimated",
                     "dep_delayed", "arr_delayed")


def make_change(kind, text):
    """One piece of news with its ntfy priority (1 low ... 5 urgent)."""
    return {"kind": kind, "priority": PRIORITY[kind], "text": text}


def keep_known_values(old, new):
    """A field that disappears from the source is not a change: keep the last known value."""
    if old is None:
        return new
    merged = dict(new)
    for key in REMEMBERED_FIELDS:
        if merged[key] is None and old.get(key) is not None:
            merged[key] = old[key]
    return merged


def find_changes(old, new, notified_delay, threshold, step):
    """Return (changes, notified_delay).

    old is the saved record (None on the first check). notified_delay is the
    delay of the last delay alert; comparing with it means slow growth
    (20 -> 30 -> 40) is still reported once it adds up to `step` minutes.
    """
    changes = []
    flight = new["flight"]
    old_status = None
    if old is not None:
        old_status = old.get("status")

    if new["status"] != old_status:
        if new["status"] == "cancelled":
            changes.append(make_change("cancelled", f"{flight} has been CANCELLED"))
        elif new["status"] == "diverted":
            changes.append(make_change("diverted", f"{flight} has been diverted"))
        elif new["status"] == "active" and old_status == "scheduled":
            changes.append(make_change("departed", f"{flight} has departed"))
    if new["status"] in ("cancelled", "diverted"):
        return changes, notified_delay

    delay = delay_of(new)
    if delay is not None:
        if delay >= threshold:
            if notified_delay is None:
                changes.append(make_change("delay", f"{flight} is delayed {delay} min (alert threshold {threshold} min)"))
                notified_delay = delay
            elif delay - notified_delay >= step:
                changes.append(make_change("delay_up", f"{flight} delay grew from {notified_delay} to {delay} min"))
                notified_delay = delay
        elif notified_delay is not None:
            changes.append(make_change("delay_over", f"{flight} is back under the threshold: {delay} min late"))
            notified_delay = None

    if old is not None:
        old_gate = old.get("dep_gate")
        if new["dep_gate"] is not None and new["dep_gate"] != old_gate:
            if old_gate is None:
                text = f"{flight} departure gate assigned: {new['dep_gate']}"
            else:
                text = f"{flight} gate changed: {old_gate} -> {new['dep_gate']}"
            changes.append(make_change("gate", text))
        old_time = old.get("dep_time")
        if new["dep_time"] is not None and old_time is not None and new["dep_time"] != old_time:
            changes.append(make_change("time", f"{flight} scheduled departure changed: {old_time} -> {new['dep_time']}"))
    return changes, notified_delay
