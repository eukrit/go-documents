"""Project email-loop directory lookup.

Reads `go_project_email_loops` from the `go-sales-orders` Firestore database
to get the canonical to/cc/bcc recipient list for a given SO reference,
used when submitting generated documents (quotations, AQ, inspection reports)
back to the customer.

Usage:
    from project_email_loops import get_recipients

    loop = get_recipients("SO26-017")
    # -> {"to": ["tikamporn@hht.co.th", "meechai@hht.co.th"],
    #     "cc": [...], "bcc": [], "projectName": "...", "confidence": "manual"}

Canonical collection schema (doc id = SO ref, "_" instead of space):
    soNumber:    str
    projectName: str
    to|cc|bcc:   [ {name, email, org, internal} ]
    source:      "manual" | "gmail_backfill"
    confidence:  "manual" | "HIGH" | "MEDIUM" | "LOW"

Populated by `go-sales-orders/backfill_email_loops.py`.
"""
from __future__ import annotations

from typing import TypedDict

from google.cloud import firestore

SOURCE_DATABASE = "go-sales-orders"
COLLECTION = "go_project_email_loops"


class Contact(TypedDict, total=False):
    name: str
    email: str
    org: str
    internal: bool


class EmailLoop(TypedDict, total=False):
    soNumber: str
    projectName: str
    to: list[Contact]
    cc: list[Contact]
    bcc: list[Contact]
    source: str
    confidence: str


def _db() -> firestore.Client:
    if not hasattr(_db, "_client"):
        _db._client = firestore.Client(database=SOURCE_DATABASE)
    return _db._client


def _doc_id(so_ref: str) -> str:
    return so_ref.strip().replace(" ", "_")


def get_loop(so_ref: str) -> EmailLoop | None:
    """Return the full email-loop document for an SO, or None if missing."""
    snap = _db().collection(COLLECTION).document(_doc_id(so_ref)).get()
    return snap.to_dict() if snap.exists else None


def get_recipients(
    so_ref: str,
    *,
    internal_only: bool = False,
    external_only: bool = False,
    min_confidence: str = "MEDIUM",
) -> dict[str, list[str]] | None:
    """Flat {to, cc, bcc} of email addresses for the SO.

    Filters:
        internal_only: only @goco.bz addresses
        external_only: only non-@goco.bz addresses
        min_confidence: drop docs below this level ("HIGH" | "MEDIUM" | "LOW"
                       | "manual"). "manual" always passes.
    """
    loop = get_loop(so_ref)
    if not loop:
        return None

    order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "manual": 4}
    conf = loop.get("confidence") or "manual"
    if order.get(conf, 0) < order.get(min_confidence, 2):
        return None

    def _emails(bucket: list[Contact]) -> list[str]:
        out = []
        for c in bucket or []:
            email = (c.get("email") or "").lower()
            if not email:
                continue
            if internal_only and not c.get("internal"):
                continue
            if external_only and c.get("internal"):
                continue
            out.append(email)
        return out

    return {
        "to": _emails(loop.get("to", [])),
        "cc": _emails(loop.get("cc", [])),
        "bcc": _emails(loop.get("bcc", [])),
        "projectName": loop.get("projectName", ""),
        "confidence": conf,
    }
