"""Slack notifier for submission events. Reads `slack-bot-token` from Secret Manager.

Channels:
    material -> #submission-materials
    drawing  -> #submission-drawings
"""
from __future__ import annotations

import json
import os
import urllib.request

from google.cloud import secretmanager

PROJECT_ID = os.environ.get("GCP_PROJECT", "ai-agents-go")
SECRET_NAME = os.environ.get("SLACK_TOKEN_SECRET", "slack-bot-token")

CHANNELS = {
    "material": "#submission-materials",
    "drawing": "#submission-drawings",
}

_token_cache: dict[str, str] = {}


def _get_token() -> str:
    if "t" in _token_cache:
        return _token_cache["t"]
    sm = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
    resp = sm.access_secret_version(request={"name": name})
    tok = resp.payload.data.decode("utf-8").strip()
    _token_cache["t"] = tok
    return tok


def _post(method: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_get_token()}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def notify(event: dict, dashboard_base_url: str = "") -> dict:
    """Send a Slack message for a submission event."""
    kind = event.get("type", "material")
    channel = CHANNELS.get(kind, CHANNELS["material"])
    sid = event.get("submissionId", "")
    so = event.get("soRef", "")
    pname = event.get("projectName", "")
    status = event.get("status", "")
    ev_name = event.get("event", "")

    verb = {
        "created": "Created",
        "sent": "Sent to customer",
        "status_changed": f"Status → *{status}*",
    }.get(ev_name, ev_name)

    link = f"{dashboard_base_url.rstrip('/')}/submissions/{sid}" if dashboard_base_url else ""
    label = "Material" if kind == "material" else "Drawing"

    blocks = [
        {"type": "header",
         "text": {"type": "plain_text", "text": f"{label} Submission — {verb}"}},
        {"type": "section",
         "fields": [
             {"type": "mrkdwn", "text": f"*ID:*\n{sid}"},
             {"type": "mrkdwn", "text": f"*SO:*\n{so}"},
             {"type": "mrkdwn", "text": f"*Project:*\n{pname}"},
             {"type": "mrkdwn", "text": f"*Status:*\n{status}"},
         ]},
    ]
    if link:
        blocks.append({
            "type": "actions",
            "elements": [{
                "type": "button",
                "text": {"type": "plain_text", "text": "Open"},
                "url": link,
                "style": "primary",
            }],
        })

    return _post("chat.postMessage", {
        "channel": channel,
        "text": f"{label} Submission {sid} — {verb}",
        "blocks": blocks,
    })
