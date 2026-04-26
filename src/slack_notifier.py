"""Slack notifier for submission events.

Resolves channels via the central Slack Router (data-communications
`route_event` HTTP endpoint), which fans out across:
  1. SO/DP project channels (#so26-XXX) — from `slack_channels.soNumber`
  2. Subcategory map (#submission-materials / #submission-drawings)
  3. Customer/vendor entity channels (#customer-<name>)
  4. Catchall — only if everything else misses

Falls back to the legacy hardcoded channel set if the router is unreachable
so we never go silent.

Auth: shared bearer token from Secret Manager (`data-comms-router-token`).
Posting: Slack `chat.postMessage` with the existing block-kit card.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request

from google.cloud import secretmanager

PROJECT_ID = os.environ.get("GCP_PROJECT", "ai-agents-go")
SLACK_TOKEN_SECRET = os.environ.get("SLACK_TOKEN_SECRET", "slack-bot-token")
ROUTER_TOKEN_SECRET = os.environ.get("ROUTER_TOKEN_SECRET", "data-comms-router-token")
SLACK_ROUTER_URL = os.environ.get("SLACK_ROUTER_URL", "")

# Legacy hardcoded fallback — used if the router is unreachable.
_FALLBACK_CHANNELS = {
    "material": "#submission-materials",
    "drawing": "#submission-drawings",
}

# In-process cache: (type, soRef) -> (channels, expires_at)
_route_cache: dict[tuple[str, str], tuple[list[dict], float]] = {}
_CACHE_TTL = 300  # 5 minutes

_secret_cache: dict[str, str] = {}
log = logging.getLogger("slack_notifier")


def _get_secret(name: str) -> str:
    if name in _secret_cache:
        return _secret_cache[name]
    sm = secretmanager.SecretManagerServiceClient()
    full = f"projects/{PROJECT_ID}/secrets/{name}/versions/latest"
    resp = sm.access_secret_version(request={"name": full})
    val = resp.payload.data.decode("utf-8").strip()
    _secret_cache[name] = val
    return val


def _post(method: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_get_secret(SLACK_TOKEN_SECRET)}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _subcategory_for(submission_type: str) -> str:
    return f"submission_{submission_type}"


def _resolve_channels(submission_type: str, so_ref: str,
                      customer_name: str = "") -> list[dict]:
    """Call the Slack Router and return the resolved channel list.

    Cached 5 min by (type, soRef). Returns the legacy hardcoded fallback if
    the router is unreachable or misconfigured.
    """
    key = (submission_type, so_ref)
    now = time.time()
    cached = _route_cache.get(key)
    if cached and cached[1] > now:
        return cached[0]

    if not SLACK_ROUTER_URL:
        log.info("SLACK_ROUTER_URL unset; using fallback channel")
        return _fallback(submission_type)

    payload = {
        "subCategory": _subcategory_for(submission_type),
        "soNumbers": [so_ref] if so_ref else [],
    }
    if customer_name:
        payload["customerName"] = customer_name

    try:
        req = urllib.request.Request(
            SLACK_ROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Auth-Token": _get_secret(ROUTER_TOKEN_SECRET),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        channels = data.get("channels", [])
        if not channels:
            channels = _fallback(submission_type)
        _route_cache[key] = (channels, now + _CACHE_TTL)
        return channels
    except Exception as e:
        log.warning("router call failed: %s: %s", type(e).__name__, e)
        return _fallback(submission_type)


def _fallback(submission_type: str) -> list[dict]:
    name = _FALLBACK_CHANNELS.get(submission_type, _FALLBACK_CHANNELS["material"])
    return [{"channelId": name, "channelName": name.lstrip("#"),
             "reason": "fallback: router unreachable"}]


def _build_blocks(event: dict, dashboard_base_url: str) -> tuple[str, list[dict]]:
    kind = event.get("type", "material")
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

    label = "Material" if kind == "material" else "Drawing"
    link = f"{dashboard_base_url.rstrip('/')}/submissions/{sid}" if dashboard_base_url else ""
    drive_link = (event.get("extra") or {}).get("driveWebViewLink", "")

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

    actions = []
    if link:
        actions.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Open"},
            "url": link, "style": "primary",
        })
    if drive_link:
        actions.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Drive (Sign)"},
            "url": drive_link,
        })
    if actions:
        blocks.append({"type": "actions", "elements": actions})

    text = f"{label} Submission {sid} — {verb}"
    return text, blocks


def notify(event: dict, dashboard_base_url: str = "") -> dict:
    """Resolve channels via Slack Router, then post to each.

    Returns: {posted: [channelName...], failed: [{channel, error}, ...]}
    """
    kind = event.get("type", "material")
    so = event.get("soRef", "")
    customer = (event.get("extra") or {}).get("customerName", "")

    channels = _resolve_channels(kind, so, customer)
    text, blocks = _build_blocks(event, dashboard_base_url)

    posted, failed = [], []
    for ch in channels:
        ch_id = ch.get("channelId") or ch.get("channelName")
        if not ch_id:
            continue
        try:
            resp = _post("chat.postMessage", {
                "channel": ch_id, "text": text, "blocks": blocks,
            })
            if resp.get("ok"):
                posted.append(ch.get("channelName") or ch_id)
            else:
                failed.append({"channel": ch_id, "error": resp.get("error", "unknown")})
        except Exception as e:
            failed.append({"channel": ch_id, "error": f"{type(e).__name__}: {e}"})

    return {"posted": posted, "failed": failed, "resolvedCount": len(channels)}
