"""Gmail sender for submissions — sends as eukrit@goco.bz via DWD, applies label.

Uses Application Default Credentials (Cloud Run SA `claude@ai-agents-go`) with
Domain-Wide Delegation to impersonate `eukrit@goco.bz`. The SA must be granted
DWD for scopes `gmail.send` and `gmail.modify` in the Workspace admin console.

Public API:
    send_submission_email(submission, pdf_bytes, attachments, recipients) -> message_id
"""
from __future__ import annotations

import base64
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import google.auth
from googleapiclient.discovery import build

from submission_clause import acceptance_clause_text

SENDER = os.environ.get("SUBMISSION_SENDER", "eukrit@goco.bz")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]

LABEL_MATERIAL = "Submissions/Materials"
LABEL_DRAWING = "Submissions/Drawings"


def _gmail_service():
    creds, _ = google.auth.default(scopes=SCOPES)
    # DWD impersonation
    if hasattr(creds, "with_subject"):
        creds = creds.with_subject(SENDER)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _get_label_id(svc, name: str) -> str | None:
    res = svc.users().labels().list(userId="me").execute()
    for lbl in res.get("labels", []):
        if lbl["name"] == name:
            return lbl["id"]
    return None


def ensure_labels() -> dict[str, str]:
    """Create Submissions/Materials and Submissions/Drawings if missing; return name->id."""
    svc = _gmail_service()
    out = {}
    for name in (LABEL_MATERIAL, LABEL_DRAWING):
        lid = _get_label_id(svc, name)
        if not lid:
            body = {
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            lid = svc.users().labels().create(userId="me", body=body).execute()["id"]
        out[name] = lid
    return out


def _label_for_kind(kind: str) -> str:
    return LABEL_MATERIAL if kind == "material" else LABEL_DRAWING


def send_submission_email(
    *,
    submission: dict,
    pdf_bytes: bytes,
    pdf_filename: str,
    attachments: list[tuple[str, bytes, str]],  # (filename, bytes, content_type)
    to: list[str],
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    subject: str | None = None,
    body_text: str | None = None,
    include_acceptance_clause: bool = True,
) -> str:
    """Send submission email. Returns Gmail message id. Applies the Submissions label.

    The bilingual EN+TH "Acceptance & Response Period" clause is appended to
    every email body unless `include_acceptance_clause=False`. Single source of
    truth: `submission_clause.acceptance_clause_text()`.
    """
    svc = _gmail_service()
    kind = submission["type"]
    sid = submission["submissionId"]
    so = submission.get("soRef", "")
    pname = submission.get("projectName", "")

    if not subject:
        label = "Material Submission" if kind == "material" else "Drawing Submission"
        subject = f"[{sid}] {label} — {pname} ({so})"

    if not body_text:
        body_text = (
            f"Dear team,\n\n"
            f"Please find attached {sid} for project {pname} ({so}).\n\n"
            f"Submission type: {submission.get('submissionType', 'Initial')} "
            f"(Rev. {submission.get('revision', '00')})\n"
            f"Items: {len(submission.get('items', []))}\n\n"
            f"Kindly review and return with your comments.\n\n"
            f"Best regards,\n"
            f"GO Corporation — Project Division\n"
        )

    if include_acceptance_clause:
        clause = acceptance_clause_text(submission)
        body_text = f"{body_text.rstrip()}\n\n---\n\n{clause}\n"

    msg = MIMEMultipart()
    msg["From"] = SENDER
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    # Submission PDF
    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
    msg.attach(pdf_part)

    # User attachments
    for fname, data, ctype in attachments:
        maintype, _, subtype = (ctype or "application/octet-stream").partition("/")
        part = MIMEApplication(data, _subtype=subtype or "octet-stream")
        part.add_header("Content-Disposition", "attachment", filename=fname)
        msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = svc.users().messages().send(
        userId="me", body={"raw": raw},
    ).execute()
    msg_id = sent["id"]

    # Apply Submissions label (filters don't reliably match outgoing mail,
    # so label is applied directly on the sent message).
    labels = ensure_labels()
    label_id = labels[_label_for_kind(kind)]
    svc.users().messages().modify(
        userId="me", id=msg_id,
        body={"addLabelIds": [label_id]},
    ).execute()

    return msg_id
