"""Upload submission PDFs to the GO Submissions Shared Drive.

Folder layout:
    My Drive root (Shared Drive "GO Submissions")
      └─ Submissions/
           └─ <soRef>/
                └─ <submissionId>.pdf

Uses Application Default Credentials (Cloud Run SA `claude@ai-agents-go`) with
Domain-Wide Delegation to impersonate `eukrit@goco.bz`. The SA must be granted
DWD for scope `drive.file` AND added as Content Manager on the Shared Drive.

Public API:
    upload_submission_pdf(pdf_bytes, submission) -> {fileId, webViewLink}
"""
from __future__ import annotations

import io
import os

import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SENDER = os.environ.get("SUBMISSION_SENDER", "eukrit@goco.bz")
SHARED_DRIVE_NAME = os.environ.get("SUBMISSIONS_DRIVE_NAME", "GO Submissions")
SHARED_DRIVE_ID = os.environ.get("SUBMISSIONS_DRIVE_ID")  # set if known
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

_FOLDER_MIME = "application/vnd.google-apps.folder"


def _drive_service():
    creds, _ = google.auth.default(scopes=SCOPES)
    if hasattr(creds, "with_subject"):
        creds = creds.with_subject(SENDER)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _resolve_shared_drive_id(svc) -> str:
    """Return the Shared Drive ID for SHARED_DRIVE_NAME, or env override."""
    if SHARED_DRIVE_ID:
        return SHARED_DRIVE_ID
    res = svc.drives().list(q=f"name = '{SHARED_DRIVE_NAME}'", pageSize=10).execute()
    drives = res.get("drives", [])
    if not drives:
        raise RuntimeError(
            f"Shared Drive '{SHARED_DRIVE_NAME}' not found. "
            "Create it and add claude@ai-agents-go as Content Manager."
        )
    return drives[0]["id"]


def _find_or_create_folder(svc, name: str, parent_id: str, drive_id: str) -> str:
    """Find a folder by exact name under parent within the Shared Drive, or create it."""
    safe_name = name.replace("'", "\\'")
    q = (
        f"name = '{safe_name}' and mimeType = '{_FOLDER_MIME}' "
        f"and '{parent_id}' in parents and trashed = false"
    )
    res = svc.files().list(
        q=q,
        corpora="drive",
        driveId=drive_id,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields="files(id, name)",
        pageSize=10,
    ).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]

    body = {"name": name, "mimeType": _FOLDER_MIME, "parents": [parent_id]}
    created = svc.files().create(
        body=body, supportsAllDrives=True, fields="id",
    ).execute()
    return created["id"]


def upload_submission_pdf(pdf_bytes: bytes, submission: dict) -> dict:
    """Upload the submission PDF to the Shared Drive and return file metadata.

    Returns: {"fileId": str, "webViewLink": str, "folderId": str}
    """
    svc = _drive_service()
    drive_id = _resolve_shared_drive_id(svc)

    # Submissions/ → <soRef>/
    submissions_folder = _find_or_create_folder(svc, "Submissions", drive_id, drive_id)
    so_ref = submission.get("soRef") or "_unspecified"
    project_folder = _find_or_create_folder(svc, so_ref, submissions_folder, drive_id)

    sid = submission["submissionId"]
    filename = f"{sid}.pdf"

    media = MediaIoBaseUpload(
        io.BytesIO(pdf_bytes), mimetype="application/pdf", resumable=False,
    )
    body = {"name": filename, "parents": [project_folder]}
    created = svc.files().create(
        body=body,
        media_body=media,
        supportsAllDrives=True,
        fields="id, webViewLink",
    ).execute()

    return {
        "fileId": created["id"],
        "webViewLink": created.get("webViewLink", ""),
        "folderId": project_folder,
    }
