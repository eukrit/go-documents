"""Ensure Slack channels #submission-materials and #submission-drawings exist
and invite the bot into them. Idempotent.

Usage:
    python scripts/setup_slack_channels.py
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, "src")

from slack_notifier import _get_token  # noqa: E402

CHANNELS = ["submission-materials", "submission-drawings"]


def _post(method, body):
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_get_token()}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _find_channel(name):
    cursor = ""
    while True:
        url = "https://slack.com/api/conversations.list?limit=1000&exclude_archived=true"
        if cursor:
            url += f"&cursor={cursor}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {_get_token()}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        for c in data.get("channels", []):
            if c["name"] == name:
                return c
        cursor = data.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            return None


def main():
    for name in CHANNELS:
        existing = _find_channel(name)
        if existing:
            print(f"  #{name:28s} exists (id={existing['id']})")
            continue
        print(f"  Creating #{name}...")
        res = _post("conversations.create", {"name": name, "is_private": False})
        if not res.get("ok"):
            print(f"    FAIL: {res.get('error')}")
            continue
        cid = res["channel"]["id"]
        print(f"    created id={cid}")
    print("OK")


if __name__ == "__main__":
    main()
