"""Publish submission lifecycle events to Pub/Sub topic `submission-events`.

The Cloud Run service publishes on create/send/status-change. A push
subscription delivers events back to this same service at POST /pubsub/push,
which fans them out to Slack (#submission-materials / #submission-drawings)
and updates the dashboard row.

Event schema (JSON message data, base64-decoded by the push receiver):
    {
      "event": "created" | "sent" | "status_changed",
      "submissionId": "MS-SO26-017-001",
      "type": "material" | "drawing",
      "soRef": "SO26-017",
      "projectName": "...",
      "status": "draft" | "sent" | "...",
      "timestamp": "2026-04-24T08:00:00Z",
      "extra": {...}
    }
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from google.cloud import pubsub_v1

PROJECT_ID = os.environ.get("GCP_PROJECT", "ai-agents-go")
TOPIC = os.environ.get("SUBMISSION_EVENTS_TOPIC", "submission-events")


def _publisher() -> pubsub_v1.PublisherClient:
    if not hasattr(_publisher, "_client"):
        _publisher._client = pubsub_v1.PublisherClient()
    return _publisher._client


def _topic_path() -> str:
    return _publisher().topic_path(PROJECT_ID, TOPIC)


def publish_event(
    *, event: str, submission: dict, extra: dict | None = None,
) -> str:
    """Publish a submission event. Returns the Pub/Sub message id."""
    payload = {
        "event": event,
        "submissionId": submission["submissionId"],
        "type": submission["type"],
        "soRef": submission.get("soRef", ""),
        "projectName": submission.get("projectName", ""),
        "status": submission.get("status", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "extra": extra or {},
    }
    data = json.dumps(payload).encode("utf-8")
    future = _publisher().publish(_topic_path(), data, event=event, type=submission["type"])
    return future.result(timeout=10)
