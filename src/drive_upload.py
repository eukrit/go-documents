"""Upload submission PDFs to the "Submissions GO" Drive folder.

Folder layout:
    "Submissions GO" (root, id from SUBMISSIONS_DRIVE_FOLDER_ID env)
      └─ <soRef>/
           └─ <submissionId>.pdf

The root folder ID is set at deploy time. Works whether the root is a Shared
Drive subfolder or a My Drive folder — `supportsAllDrives=True` covers both.

Uses Application Default Credentials (Cloud Run SA `claude@ai-agents-go`) with
Domain-Wide Delegation to impersonate `eukrit@goco.bz`. The SA must be granted
DWD for scope `drive.file` AND `eukrit@goco.bz` must have Editor access on the
root folder.

Public API:
    upload_submission_pdf(pdf_bytes, submission) -> {fileId, webViewLink, folderId}
"""
from __future__ import annotations

import io
import os

import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SENDER = os.environ.get("SUBMISSION_SENDER", "eukrit@goco.bz")

# "Submissions GO" Drive folder — pre-created by Eukrit.
# https://drive.google.com/drive/folders/1gAhGAI94Z96aFUm3nCp66QO573ixm-Vh
SUBMISSIONS_FOLDER_ID = os.environ.get(
    "SUBMISSIONS_DRIVE_FOLDER_ID",
    "1gAhGAI94Z96aFUm3nCp66QO573ixm-Vh",
)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
_FOLDER_MIME = "application/vnd.google-apps.folder"


def _drive_service():
    creds, _ = google.auth.default(scopes=SCOPES)
    if hasattr(creds, "with_subject"):
        creds = creds.with_subject(SENDER)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _find_or_create_folder(svc, name: str, parent_id: str) -> str:
    """Find a folder by exact name under parent (covers both My Drive and Shared
    Drive). Creates if missing."""
    safe_name = name.replace("'", "\\'")
    q = (
        f"name = '{safe_name}' and mimeType = '{_FOLDER_MIME}' "
        f"and '{parent_id}' in parents and trashed = false"
    )
    res = svc.files().list(
        q=q,
        corpora="allDrives",
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
    """Upload the submission PDF to "Submissions GO/<soRef>/<sid>.pdf".

    Returns: {"fileId": str, "webViewLink": str, "folderId": str}
    """
    svc = _drive_service()

    so_ref = submission.get("soRef") or "_unspecified"
    project_folder = _find_or_create_folder(svc, so_ref, SUBMISSIONS_FOLDER_ID)

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
