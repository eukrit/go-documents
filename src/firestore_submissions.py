"""Firestore models + CRUD for material and drawing submissions.

Collection: `submissions` in database `go-documents`.
Doc id = submissionId (e.g. MS-SO26-017-001, DS-SO26-017-003).

Shared fields:
    submissionId:   str (doc id)
    type:           "material" | "drawing"
    soRef:          str (e.g. "SO26-017") — FK into go-sales-orders
    projectName:    str
    revision:       str (e.g. "00", "01")
    date:           str (YYYY-MM-DD)
    submissionType: "Initial" | "Resubmission"
    client:         str
    consultant:     str
    siteLocation:   str
    items:          list[dict] — material rows or drawing rows
    notes:          str
    attachments:    list[{filename, gcsPath, size, contentType, uploadedAt}]
    status:         "draft" | "sent" | "approved" | "approved_as_noted"
                    | "revise_resubmit" | "rejected"
    pdfGcsPath:     str (set after render)
    emailMessageId: str (set after send)
    emailSentAt:    timestamp
    reviewerRemarks:str
    createdAt:      timestamp
    updatedAt:      timestamp

Material-specific fields: none beyond items[] rows with
    {no, description, manufacturer, model, qty, unit}
Drawing-specific fields:
    discipline:   str
    issuePurpose: str ("For Approval" | "For Construction" | "For Record")
    drawnBy:      str
    checkedBy:    str
    items[] rows: {no, drawingNo, drawingTitle, revision, scale, sheetSize}
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from google.cloud import firestore

DATABASE = "go-documents"
COLLECTION = "submissions"
GCS_BUCKET = "go-documents-files"

SubmissionType = Literal["material", "drawing"]
STATUS_VALUES = {
    "draft", "sent", "approved", "approved_as_noted",
    "revise_resubmit", "rejected",
}


def _db() -> firestore.Client:
    if not hasattr(_db, "_client"):
        _db._client = firestore.Client(database=DATABASE)
    return _db._client


def _prefix(kind: SubmissionType) -> str:
    return {"material": "MS", "drawing": "DS"}[kind]


_SAFE_SO = re.compile(r"[^A-Za-z0-9_-]")


def _safe_so(so_ref: str) -> str:
    return _SAFE_SO.sub("", so_ref.strip().replace(" ", "_"))


def next_submission_id(kind: SubmissionType, so_ref: str) -> str:
    """Return next MS-<SO>-NNN / DS-<SO>-NNN id for the SO."""
    so = _safe_so(so_ref)
    prefix = f"{_prefix(kind)}-{so}-"
    docs = (
        _db().collection(COLLECTION)
        .where("soRef", "==", so_ref)
        .where("type", "==", kind)
        .stream()
    )
    max_n = 0
    for d in docs:
        if d.id.startswith(prefix):
            try:
                max_n = max(max_n, int(d.id[len(prefix):]))
            except ValueError:
                pass
    return f"{prefix}{max_n + 1:03d}"


def create_submission(
    *,
    kind: SubmissionType,
    so_ref: str,
    project_name: str,
    client: str = "",
    consultant: str = "",
    site_location: str = "",
    revision: str = "00",
    submission_type: str = "Initial",
    items: list[dict] | None = None,
    notes: str = "",
    # drawing-only
    discipline: str = "",
    issue_purpose: str = "",
    drawn_by: str = "",
    checked_by: str = "",
) -> dict:
    """Create a new submission record and return it (including id)."""
    sid = next_submission_id(kind, so_ref)
    now = datetime.now(timezone.utc)
    doc = {
        "submissionId": sid,
        "type": kind,
        "soRef": so_ref,
        "projectName": project_name,
        "revision": revision,
        "date": now.date().isoformat(),
        "submissionType": submission_type,
        "client": client,
        "consultant": consultant,
        "siteLocation": site_location,
        "items": items or [],
        "notes": notes,
        "attachments": [],
        "status": "draft",
        "pdfGcsPath": "",
        "emailMessageId": "",
        "reviewerRemarks": "",
        "createdAt": now,
        "updatedAt": now,
    }
    if kind == "drawing":
        doc.update({
            "discipline": discipline,
            "issuePurpose": issue_purpose,
            "drawnBy": drawn_by,
            "checkedBy": checked_by,
        })
    _db().collection(COLLECTION).document(sid).set(doc)
    return doc


def get_submission(submission_id: str) -> dict | None:
    snap = _db().collection(COLLECTION).document(submission_id).get()
    return snap.to_dict() if snap.exists else None


def list_submissions(
    *, so_ref: str | None = None, kind: SubmissionType | None = None,
    limit: int = 200,
) -> list[dict]:
    q = _db().collection(COLLECTION)
    if so_ref:
        q = q.where("soRef", "==", so_ref)
    if kind:
        q = q.where("type", "==", kind)
    q = q.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(limit)
    return [d.to_dict() for d in q.stream()]


def list_so_refs() -> list[dict]:
    """Distinct SO refs with submission counts for the master dashboard."""
    agg: dict[str, dict] = {}
    for d in _db().collection(COLLECTION).stream():
        data = d.to_dict()
        so = data.get("soRef", "")
        if not so:
            continue
        row = agg.setdefault(so, {
            "soRef": so,
            "projectName": data.get("projectName", ""),
            "material": 0, "drawing": 0, "total": 0,
            "lastUpdate": None,
        })
        row[data["type"]] = row.get(data["type"], 0) + 1
        row["total"] += 1
        upd = data.get("updatedAt")
        if upd and (row["lastUpdate"] is None or upd > row["lastUpdate"]):
            row["lastUpdate"] = upd
    return sorted(agg.values(), key=lambda r: r["lastUpdate"] or datetime.min, reverse=True)


def add_attachment(submission_id: str, att: dict) -> None:
    ref = _db().collection(COLLECTION).document(submission_id)
    ref.update({
        "attachments": firestore.ArrayUnion([att]),
        "updatedAt": datetime.now(timezone.utc),
    })


def update_status(submission_id: str, status: str, **extra) -> None:
    if status not in STATUS_VALUES:
        raise ValueError(f"invalid status: {status}")
    patch = {"status": status, "updatedAt": datetime.now(timezone.utc)}
    patch.update(extra)
    _db().collection(COLLECTION).document(submission_id).update(patch)


def mark_sent(
    submission_id: str,
    *,
    pdf_gcs_path: str,
    message_id: str,
    drive_file_id: str | None = None,
    drive_web_view_link: str | None = None,
) -> None:
    extras = {}
    if drive_file_id:
        extras["driveFileId"] = drive_file_id
    if drive_web_view_link:
        extras["driveWebViewLink"] = drive_web_view_link
    update_status(
        submission_id, "sent",
        pdfGcsPath=pdf_gcs_path,
        emailMessageId=message_id,
        emailSentAt=datetime.now(timezone.utc),
        **extras,
    )
