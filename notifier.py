"""Format alerts and deliver them with ntfy (W4: requests.post with a Bearer token).

The message lists what changed first and the raw facts separately, so the
reader can check the interpretation (W4: keep evidence separate from
interpretation). Every alert is also appended to alerts_log.txt.
"""

import os

import requests

from storage import now_utc

TIMEOUT_SEC = 10


def build_message(changes, record, source, note):
    """Return (title, body, priority) for the changes of one flight."""
    kinds = []
    lines = []
    priority = 1
    for item in changes:
        kinds.append(item["kind"])
        lines.append(f"- {item['text']}")
        if item["priority"] > priority:
            priority = item["priority"]
    if note != "":
        lines.append(f"Note: {note}")
    lines.append("")
    lines.append("Evidence:")
    lines.append(f"  source={source}  status={record['status']}  route={record['dep_iata']}->{record['arr_iata']}")
    lines.append(f"  scheduled={record['dep_time']}  estimated={record['dep_estimated']}")
    lines.append(f"  gate={record['dep_gate']}  dep_delayed={record['dep_delayed']}  arr_delayed={record['arr_delayed']}")
    lines.append(f"  checked_at={now_utc()}")
    title = f"{record['flight']}: {', '.join(kinds)}"
    return title, "\n".join(lines), priority


def send_ntfy(settings, title, body, priority):
    """POST one message to the ntfy topic; return (ok, error).

    Not retried here: repeating a POST could send the alert twice. The caller
    keeps the old state instead, so the next round tries again (W4: only
    repeat an operation when repeating its effect is acceptable).
    """
    url = f"{settings['ntfy_server']}/{settings['ntfy_topic']}"
    headers = {"Title": title, "Priority": str(priority), "Tags": "airplane"}
    token = os.environ.get(settings["ntfy_token_env"], "").strip()
    if token != "":
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.post(url, data=body.encode("utf-8"), headers=headers, timeout=TIMEOUT_SEC)
    except requests.exceptions.RequestException as exc:
        return False, f"ntfy not reachable ({type(exc).__name__})"
    if response.status_code != 200:
        return False, f"ntfy answered HTTP {response.status_code}"
    return True, ""


def write_log(path, flight, outcome, title, body):
    """Append one tab-separated line per alert (the token is never written)."""
    flat_body = body.replace("\n", " | ")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{now_utc()}\t{flight}\t{outcome}\t{title}\t{flat_body}\n")


def send_alert(settings, flight, title, body, priority, dry_run):
    """Print the alert, send it if ntfy is set up, log it. Return True when it counts as delivered."""
    print(f"\n  ALERT (priority {priority}) {title}")
    for line in body.split("\n"):
        print(f"    {line}")
    if dry_run:
        print("    -> dry run: not sent")
        return True

    delivered = True
    if settings["ntfy_topic"] == "":
        outcome = "printed only (ntfy_topic is empty)"
    else:
        delivered, error = send_ntfy(settings, title, body, priority)
        if delivered:
            outcome = "sent with ntfy"
        else:
            outcome = f"FAILED: {error}"
    print(f"    -> {outcome}")
    write_log(settings["log_file"], flight, outcome, title, body)
    return delivered


def deliver(settings, changes, record, note, dry_run):
    """Build and send the alert for the changes of one flight."""
    title, body, priority = build_message(changes, record, settings["source"], note)
    return send_alert(settings, record["flight"], title, body, priority, dry_run)
