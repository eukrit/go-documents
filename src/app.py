"""GO Documents — Document + Submission service.

Serves:
  - Document viewer (quotations, submissions, etc.) at docs.leka.studio / docs.aredaatelier.com
  - Submission creation, attachment upload, PDF render, email send
  - Master project dashboard at /dashboard
  - Per-project dashboard at /projects/<soRef>
  - Pub/Sub push receiver at /pubsub/push -> Slack + dashboard update
"""

import base64
import json
import logging
import os
from datetime import datetime, timezone

from flask import (
    Flask, Response, abort, jsonify, redirect,
    render_template_string, request,
)
from google.cloud import firestore, storage

from firestore_submissions import (
    COLLECTION as SUB_COLLECTION,
    GCS_BUCKET as SUB_BUCKET,
    add_attachment, create_submission, get_submission,
    list_so_refs, list_submissions, mark_sent, update_status,
)
from drive_upload import upload_submission_pdf
from gmail_sender import send_submission_email
from project_email_loops import get_recipients
from slack_notifier import notify as slack_notify
from submission_events import publish_event
from submission_render import render_html, render_pdf

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("go-documents")

app = Flask(__name__)

DATABASE = "go-documents"
COLLECTION = "document-records"
GCS_BUCKET = "go-documents-files"

VALID_TYPES = {
    "quotations": "quotation",
    "submissions": "submission",
    "datasheets": "datasheet",
    "certificates": "certificate",
    "sales-sheets": "sales-sheet",
}

BRAND_DOMAINS = {"areda": "docs.aredaatelier.com"}
DEFAULT_DOMAIN = "docs.leka.studio"

NOINDEX_HEADERS = {
    "X-Robots-Tag": "noindex, nofollow, noarchive, nosnippet",
    "Cache-Control": "private, no-store",
}


def get_db():
    if not hasattr(get_db, "_client"):
        get_db._client = firestore.Client(database=DATABASE)
    return get_db._client


def _gcs():
    if not hasattr(_gcs, "_client"):
        _gcs._client = storage.Client()
    return _gcs._client


def _dashboard_base() -> str:
    return os.environ.get("DASHBOARD_BASE_URL", f"https://{request.host}")


# ---------- robots / health ----------

@app.route("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain", headers=NOINDEX_HEADERS)


@app.route("/")
def index():
    return redirect("/dashboard", code=302)


@app.route("/healthz")
def healthz():
    return "ok"


# ========================================================================
# SUBMISSIONS — creation, upload, send, view
# ========================================================================

@app.route("/api/submissions", methods=["POST"])
def api_create_submission():
    body = request.get_json(silent=True) or {}
    kind = body.get("type")
    if kind not in ("material", "drawing"):
        return jsonify({"error": "type must be 'material' or 'drawing'"}), 400
    so_ref = body.get("soRef")
    if not so_ref:
        return jsonify({"error": "soRef required"}), 400

    sub = create_submission(
        kind=kind,
        so_ref=so_ref,
        project_name=body.get("projectName", ""),
        client=body.get("client", ""),
        consultant=body.get("consultant", ""),
        site_location=body.get("siteLocation", ""),
        revision=body.get("revision", "00"),
        submission_type=body.get("submissionType", "Initial"),
        items=body.get("items", []),
        notes=body.get("notes", ""),
        discipline=body.get("discipline", ""),
        issue_purpose=body.get("issuePurpose", ""),
        drawn_by=body.get("drawnBy", ""),
        checked_by=body.get("checkedBy", ""),
    )
    try:
        publish_event(event="created", submission=sub)
    except Exception as e:  # never block creation on pubsub
        log.warning("publish_event failed: %s", type(e).__name__)
    return jsonify({"submissionId": sub["submissionId"], "status": sub["status"]}), 201


@app.route("/api/submissions/<sid>/attachments", methods=["POST"])
def api_upload_attachment(sid):
    sub = get_submission(sid)
    if not sub:
        return jsonify({"error": "not found"}), 404
    if "file" not in request.files:
        return jsonify({"error": "file form-field required"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "empty filename"}), 400

    # Upload to GCS: submissions/<sid>/attachments/<filename>
    gcs_path = f"submissions/{sid}/attachments/{f.filename}"
    bucket = _gcs().bucket(SUB_BUCKET)
    blob = bucket.blob(gcs_path)
    data = f.read()
    blob.upload_from_string(data, content_type=f.mimetype or "application/octet-stream")

    att = {
        "filename": f.filename,
        "gcsPath": gcs_path,
        "size": len(data),
        "contentType": f.mimetype or "application/octet-stream",
        "uploadedAt": datetime.now(timezone.utc),
    }
    add_attachment(sid, att)
    return jsonify({"ok": True, "attachment": {**att, "uploadedAt": att["uploadedAt"].isoformat()}}), 201


@app.route("/api/submissions/<sid>/send", methods=["POST"])
def api_send_submission(sid):
    sub = get_submission(sid)
    if not sub:
        return jsonify({"error": "not found"}), 404

    loop = get_recipients(sub["soRef"])
    if not loop or not loop.get("to"):
        return jsonify({"error": f"no email loop for SO {sub['soRef']}"}), 424

    # Render PDF
    pdf_bytes = render_pdf(sub)
    pdf_filename = f"{sub['submissionId']}.pdf"

    # Upload PDF to GCS
    pdf_gcs = f"submissions/{sid}/{pdf_filename}"
    _gcs().bucket(SUB_BUCKET).blob(pdf_gcs).upload_from_string(
        pdf_bytes, content_type="application/pdf",
    )

    # Mirror to Shared Drive so eukrit can manually click "Request signature"
    # in Drive UI (Google Workspace native eSignature, no public API).
    drive_meta = {}
    try:
        drive_meta = upload_submission_pdf(pdf_bytes, sub)
    except Exception as e:
        log.warning("drive upload failed: %s: %s", type(e).__name__, e)

    # Fetch attachments from GCS
    atts = []
    for a in sub.get("attachments", []):
        blob = _gcs().bucket(SUB_BUCKET).blob(a["gcsPath"])
        atts.append((a["filename"], blob.download_as_bytes(), a.get("contentType", "application/octet-stream")))

    # Override recipients from request body if provided
    body = request.get_json(silent=True) or {}
    msg_id = send_submission_email(
        submission=sub,
        pdf_bytes=pdf_bytes,
        pdf_filename=pdf_filename,
        attachments=atts,
        to=body.get("to") or loop["to"],
        cc=body.get("cc") or loop.get("cc", []),
        bcc=body.get("bcc") or loop.get("bcc", []),
        subject=body.get("subject"),
        body_text=body.get("body"),
    )

    mark_sent(
        sid,
        pdf_gcs_path=pdf_gcs,
        message_id=msg_id,
        drive_file_id=drive_meta.get("fileId"),
        drive_web_view_link=drive_meta.get("webViewLink"),
    )
    sub = get_submission(sid)
    try:
        publish_event(event="sent", submission=sub, extra={
            "messageId": msg_id,
            "driveWebViewLink": drive_meta.get("webViewLink", ""),
            "customerName": sub.get("customerName") or sub.get("client", ""),
        })
    except Exception as e:
        log.warning("publish_event failed: %s", type(e).__name__)
    return jsonify({
        "ok": True,
        "messageId": msg_id,
        "pdfGcsPath": pdf_gcs,
        "driveFileId": drive_meta.get("fileId"),
        "driveWebViewLink": drive_meta.get("webViewLink"),
    })


@app.route("/api/submissions/<sid>/status", methods=["PATCH"])
def api_update_status(sid):
    body = request.get_json(silent=True) or {}
    status = body.get("status")
    try:
        update_status(sid, status, reviewerRemarks=body.get("reviewerRemarks", ""))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    sub = get_submission(sid)
    try:
        publish_event(event="status_changed", submission=sub)
    except Exception as e:
        log.warning("publish_event failed: %s", type(e).__name__)
    return jsonify({"ok": True})


@app.route("/submissions/<sid>")
def view_submission(sid):
    """Serve the filled HTML for the submission."""
    sub = get_submission(sid)
    if not sub:
        # Fall through to legacy document-records lookup
        return _legacy_doc("submissions", sid)
    html_text = render_html(sub)
    return Response(html_text, content_type="text/html", headers=NOINDEX_HEADERS)


@app.route("/submissions/<sid>/pdf")
def view_submission_pdf(sid):
    sub = get_submission(sid)
    if not sub:
        abort(404)
    pdf_bytes = render_pdf(sub)
    return Response(
        pdf_bytes, content_type="application/pdf",
        headers={**NOINDEX_HEADERS, "Content-Disposition": f'inline; filename="{sid}.pdf"'},
    )


# ========================================================================
# DASHBOARDS
# ========================================================================

@app.route("/dashboard")
def dashboard():
    rows = list_so_refs()
    return Response(
        render_template_string(DASHBOARD_TEMPLATE, rows=rows),
        headers=NOINDEX_HEADERS,
    )


@app.route("/projects/<so_ref>")
def project_dashboard(so_ref):
    subs = list_submissions(so_ref=so_ref)
    materials = [s for s in subs if s["type"] == "material"]
    drawings = [s for s in subs if s["type"] == "drawing"]
    project_name = subs[0]["projectName"] if subs else so_ref
    return Response(
        render_template_string(
            PROJECT_TEMPLATE,
            so_ref=so_ref, project_name=project_name,
            materials=materials, drawings=drawings,
        ),
        headers=NOINDEX_HEADERS,
    )


# ========================================================================
# PUB/SUB PUSH RECEIVER
# ========================================================================

@app.route("/pubsub/push", methods=["POST"])
def pubsub_push():
    envelope = request.get_json(silent=True) or {}
    msg = envelope.get("message", {})
    data_b64 = msg.get("data", "")
    try:
        event = json.loads(base64.b64decode(data_b64).decode("utf-8")) if data_b64 else {}
    except Exception:
        return "bad message", 400
    try:
        slack_notify(event, dashboard_base_url=_dashboard_base())
    except Exception as e:
        log.error("slack notify failed: %s", e)
        # Ack anyway — do not stack push retries on Slack transient failures
    return "", 204


# ========================================================================
# SLACK INTERACTIVITY (forwarded from slack-router service)
# ========================================================================

_slack_signing_secret_cache = {"v": ""}


def _slack_signing_secret() -> str:
    if _slack_signing_secret_cache["v"]:
        return _slack_signing_secret_cache["v"]
    val = os.environ.get("SLACK_SIGNING_SECRET", "")
    if not val:
        try:
            from google.cloud import secretmanager
            sm = secretmanager.SecretManagerServiceClient()
            project = os.environ.get("GCP_PROJECT", "ai-agents-go")
            name = (
                f"projects/{project}/secrets/"
                f"{os.environ.get('SLACK_SIGNING_SECRET_NAME', 'slack-signing-secret')}"
                "/versions/latest"
            )
            val = sm.access_secret_version(
                request={"name": name},
            ).payload.data.decode("utf-8").strip()
        except Exception as e:
            log.error("failed to load slack-signing-secret: %s", type(e).__name__)
            return ""
    _slack_signing_secret_cache["v"] = val
    return val


# Lazy import keeps cold-start small for non-Slack paths.
def _verify_slack_signature(raw_body: bytes, ts: str, sig: str) -> bool:
    import hashlib
    import hmac
    import time
    secret = _slack_signing_secret()
    if not secret or not ts or not sig:
        return False
    try:
        ts_int = int(ts)
    except ValueError:
        return False
    if abs(time.time() - ts_int) > 60 * 5:
        return False
    base = b"v0:" + ts.encode("ascii") + b":" + raw_body
    digest = hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest("v0=" + digest, sig)


def _dispatch_submission_action(action_id: str, sid: str, user_id: str,
                                  trigger_id: str, response_url: str) -> dict:
    """Dispatch a submission_* action_id to the right handler."""
    from urllib.parse import parse_qs  # noqa: F401  (imported lazily elsewhere)

    if action_id.startswith("submission_approve_"):
        update_status(sid, "approved", reviewerRemarks=f"Approved via Slack by {user_id}")
        sub = get_submission(sid)
        try:
            publish_event(event="status_changed", submission=sub,
                          extra={"reviewedBy": user_id, "via": "slack"})
        except Exception as e:
            log.warning("publish_event failed: %s", type(e).__name__)
        return {"text": f":white_check_mark: {sid} approved by <@{user_id}>"}

    if action_id.startswith("submission_reject_"):
        update_status(sid, "rejected", reviewerRemarks=f"Rejected via Slack by {user_id}")
        sub = get_submission(sid)
        try:
            publish_event(event="status_changed", submission=sub,
                          extra={"reviewedBy": user_id, "via": "slack"})
        except Exception as e:
            log.warning("publish_event failed: %s", type(e).__name__)
        return {"text": f":x: {sid} rejected by <@{user_id}>"}

    if action_id.startswith("submission_comment_"):
        # Surface the dashboard so the reviewer can drop a long-form comment.
        link = f"{_dashboard_base()}/submissions/{sid}"
        return {"response_type": "ephemeral",
                "text": f"Add a comment on {sid}: {link}"}

    # submission_open_* / submission_drive_* are URL buttons; Slack doesn't
    # actually POST those (they navigate). Defensive no-op.
    return {"text": ""}


def _post_response_url(response_url: str, body: dict) -> None:
    if not response_url:
        return
    import urllib.request
    req = urllib.request.Request(
        response_url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception as e:
        log.warning("response_url post failed: %s", type(e).__name__)


@app.route("/slack/interactivity", methods=["POST"])
def slack_interactivity():
    """Receive Slack button clicks forwarded by the slack-router dispatcher.

    slack-router/server.py forwards original Slack body + signature headers,
    so we re-verify here (defense-in-depth) using SLACK_SIGNING_SECRET — same
    secret slack-router uses.
    """
    raw_body = request.get_data(cache=False)
    ts = request.headers.get("X-Slack-Request-Timestamp", "")
    sig = request.headers.get("X-Slack-Signature", "")

    if not _verify_slack_signature(raw_body, ts, sig):
        return ("invalid signature", 401)

    from urllib.parse import parse_qs
    form = parse_qs(raw_body.decode("utf-8"))
    raw_payload = form.get("payload", [""])[0]
    if not raw_payload:
        return ("no payload", 400)

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return ("bad json", 400)

    actions = payload.get("actions") or []
    if not actions:
        return ("", 200)
    action = actions[0]
    action_id = action.get("action_id", "")
    sid = action.get("value") or _sid_from_action_id(action_id)
    user_id = (payload.get("user") or {}).get("id", "")
    trigger_id = payload.get("trigger_id", "")
    response_url = payload.get("response_url", "")

    if not action_id.startswith("submission_"):
        return ("unrouted action_id", 400)

    if not sid:
        return ("missing submission id", 400)

    try:
        body = _dispatch_submission_action(
            action_id, sid, user_id, trigger_id, response_url,
        )
    except ValueError as e:
        body = {"response_type": "ephemeral",
                "text": f":warning: {str(e)}"}
    except Exception as e:
        log.error("interactivity dispatch failed: %s", e)
        body = {"response_type": "ephemeral",
                "text": ":warning: Internal error — see logs."}

    if body and body.get("text"):
        _post_response_url(response_url, body)

    return ("", 200)


def _sid_from_action_id(action_id: str) -> str:
    """Extract the submission id from action_ids like submission_approve_MS-SO26-017-001."""
    parts = action_id.split("_", 2)
    return parts[2] if len(parts) >= 3 else ""


# ========================================================================
# LEGACY document-records viewer (quotations / datasheets / etc.)
# ========================================================================

def _legacy_doc(doc_type_path, doc_id):
    doc_type = VALID_TYPES.get(doc_type_path)
    if not doc_type:
        abort(404)
    db = get_db()
    doc = db.collection(COLLECTION).document(doc_id).get()
    if not doc.exists:
        abort(404)
    data = doc.to_dict()
    if data.get("document_type") != doc_type:
        abort(404)
    redir = _maybe_redirect(data, doc_type_path, doc_id)
    if redir:
        return redir
    gcs_html_path = data.get("generated_html_gcs")
    if gcs_html_path:
        try:
            blob = _gcs().bucket(GCS_BUCKET).blob(gcs_html_path)
            return Response(blob.download_as_text(), content_type="text/html", headers=NOINDEX_HEADERS)
        except Exception:
            pass
    html_content = data.get("html_content")
    if html_content:
        return Response(html_content, content_type="text/html", headers=NOINDEX_HEADERS)
    return Response(
        render_template_string(
            DOC_FALLBACK_TEMPLATE,
            code=data.get("quotation_code", doc_id),
            lang=data.get("language", "en"),
            subject=data.get("subject", ""),
            status=data.get("status", "draft"),
            grand_total=f"{data.get('grand_total', 0):,.2f}",
            currency=data.get("currency", "THB"),
            doc_type=doc_type_path, doc_id=doc_id,
        ),
        content_type="text/html", headers=NOINDEX_HEADERS,
    )


def _get_canonical_domain(template_id: str) -> str:
    for prefix, domain in BRAND_DOMAINS.items():
        if template_id.startswith(prefix):
            return domain
    return DEFAULT_DOMAIN


def _maybe_redirect(data, doc_type_path, doc_id):
    canonical = _get_canonical_domain(data.get("template_id", ""))
    if request.host.split(":")[0] != canonical:
        return redirect(f"https://{canonical}/{doc_type_path}/{doc_id}", code=301)
    return None


@app.route("/<doc_type_path>")
def list_documents(doc_type_path):
    doc_type = VALID_TYPES.get(doc_type_path)
    if not doc_type:
        abort(404)
    if doc_type_path == "submissions":
        # Prefer new submissions collection
        items = []
        for s in list_submissions(limit=200):
            items.append({
                "id": s["submissionId"], "code": s["submissionId"],
                "subject": f"{s.get('projectName', '')} ({s.get('soRef', '')})",
                "language": s["type"],
                "status": s.get("status", "draft"),
                "date": s.get("date", ""),
                "url": f"/submissions/{s['submissionId']}",
            })
        return Response(
            render_template_string(LIST_TEMPLATE, doc_type=doc_type_path, items=items),
            headers=NOINDEX_HEADERS,
        )
    db = get_db()
    docs = (
        db.collection(COLLECTION)
        .where("document_type", "==", doc_type)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(100).stream()
    )
    items = []
    for doc in docs:
        d = doc.to_dict()
        items.append({
            "id": doc.id, "code": d.get("quotation_code", doc.id),
            "subject": d.get("subject", ""),
            "language": d.get("language", ""),
            "status": d.get("status", ""),
            "date": str(d.get("document_date", ""))[:10],
            "url": f"/{doc_type_path}/{doc.id}",
        })
    return Response(
        render_template_string(LIST_TEMPLATE, doc_type=doc_type_path, items=items),
        headers=NOINDEX_HEADERS,
    )


@app.route("/<doc_type_path>/<doc_id>")
def serve_document(doc_type_path, doc_id):
    if doc_type_path == "submissions":
        return view_submission(doc_id)
    return _legacy_doc(doc_type_path, doc_id)


# ========================================================================
# Templates
# ========================================================================

_BASE_CSS = """
body { font-family: 'Manrope', system-ui, sans-serif; margin: 40px; color: #182557; background: #F5F4F0; }
h1 { font-size: 24px; margin-bottom: 8px; }
h2 { font-size: 16px; margin: 24px 0 10px; color: #8003FF; text-transform: uppercase; letter-spacing: 1px; }
.sub { color: #928A83; font-size: 13px; margin-bottom: 24px; }
table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 32px; }
th { background: #182557; color: #FFF9E6; text-align: left; padding: 10px 16px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; }
td { padding: 10px 16px; border-bottom: 1px solid #ECEAE4; font-size: 13px; }
a { color: #182557; text-decoration: none; font-weight: 600; }
a:hover { text-decoration: underline; }
.status { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
.s-draft { background: #FEF3C7; color: #92400E; }
.s-sent { background: #DBEAFE; color: #1E40AF; }
.s-approved { background: #D1FAE5; color: #065F46; }
.s-approved_as_noted { background: #D1FAE5; color: #065F46; }
.s-revise_resubmit { background: #FEE2E2; color: #991B1B; }
.s-rejected { background: #FEE2E2; color: #991B1B; }
.badge { display:inline-block; padding: 2px 8px; background:#F3F4F6; color:#374151; border-radius:4px; font-size:11px; margin-right:4px; }
.empty { text-align: center; padding: 40px; color: #928A83; }
.crumb { color:#928A83; font-size:12px; margin-bottom:8px; }
.crumb a { color:#8003FF; font-weight:600; }
"""

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="robots" content="noindex">
<title>GO Documents — Project Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>""" + _BASE_CSS + """</style>
</head><body>
<h1>Project Document Dashboard</h1>
<div class="sub">All sales-order projects with active submissions · <a href="/submissions">all submissions</a></div>
{% if rows %}
<table>
<thead><tr><th>SO Ref</th><th>Project</th><th>Materials</th><th>Drawings</th><th>Total</th><th>Last update</th><th></th></tr></thead>
<tbody>
{% for r in rows %}
<tr>
  <td><a href="/projects/{{ r.soRef }}">{{ r.soRef }}</a></td>
  <td>{{ r.projectName }}</td>
  <td>{{ r.material }}</td>
  <td>{{ r.drawing }}</td>
  <td><b>{{ r.total }}</b></td>
  <td>{{ (r.lastUpdate.isoformat() if r.lastUpdate else "")[:19] }}</td>
  <td><a href="/projects/{{ r.soRef }}">Open →</a></td>
</tr>
{% endfor %}
</tbody></table>
{% else %}
<div class="empty">No projects with submissions yet.</div>
{% endif %}
</body></html>"""

PROJECT_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="robots" content="noindex">
<title>{{ so_ref }} — Submissions</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>""" + _BASE_CSS + """</style>
</head><body>
<div class="crumb"><a href="/dashboard">← Dashboard</a></div>
<h1>{{ project_name }}</h1>
<div class="sub"><span class="badge">{{ so_ref }}</span> {{ materials|length }} material · {{ drawings|length }} drawing</div>

<h2>Material Submissions</h2>
{% if materials %}
<table>
<thead><tr><th>ID</th><th>Rev</th><th>Items</th><th>Date</th><th>Status</th><th></th></tr></thead>
<tbody>
{% for s in materials %}
<tr>
  <td><a href="/submissions/{{ s.submissionId }}">{{ s.submissionId }}</a></td>
  <td>{{ s.revision }}</td>
  <td>{{ s['items']|length }}</td>
  <td>{{ s.date }}</td>
  <td><span class="status s-{{ s.status }}">{{ s.status }}</span></td>
  <td><a href="/submissions/{{ s.submissionId }}/pdf">PDF</a></td>
</tr>
{% endfor %}
</tbody></table>
{% else %}<div class="empty">No material submissions.</div>{% endif %}

<h2>Drawing Submissions</h2>
{% if drawings %}
<table>
<thead><tr><th>ID</th><th>Rev</th><th>Discipline</th><th>Purpose</th><th>Sheets</th><th>Date</th><th>Status</th><th></th></tr></thead>
<tbody>
{% for s in drawings %}
<tr>
  <td><a href="/submissions/{{ s.submissionId }}">{{ s.submissionId }}</a></td>
  <td>{{ s.revision }}</td>
  <td>{{ s.discipline }}</td>
  <td>{{ s.issuePurpose }}</td>
  <td>{{ s['items']|length }}</td>
  <td>{{ s.date }}</td>
  <td><span class="status s-{{ s.status }}">{{ s.status }}</span></td>
  <td><a href="/submissions/{{ s.submissionId }}/pdf">PDF</a></td>
</tr>
{% endfor %}
</tbody></table>
{% else %}<div class="empty">No drawing submissions.</div>{% endif %}
</body></html>"""

LIST_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="robots" content="noindex">
<title>GO Documents — {{ doc_type }}</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>""" + _BASE_CSS + """</style>
</head><body>
<div class="crumb"><a href="/dashboard">← Dashboard</a></div>
<h1>{{ doc_type|capitalize }}</h1>
{% if items %}
<table><thead><tr><th>Code</th><th>Subject</th><th>Type</th><th>Date</th><th>Status</th></tr></thead><tbody>
{% for item in items %}
<tr><td><a href="{{ item.url }}">{{ item.code }}</a></td><td>{{ item.subject }}</td>
<td>{{ item.language|upper }}</td><td>{{ item.date }}</td>
<td><span class="status s-{{ item.status }}">{{ item.status }}</span></td></tr>
{% endfor %}
</tbody></table>
{% else %}<div class="empty">No {{ doc_type }} found.</div>{% endif %}
</body></html>"""

DOC_FALLBACK_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="robots" content="noindex">
<title>{{ code }} — GO Documents</title>
<style>""" + _BASE_CSS + """
.card { background: white; padding: 32px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); max-width:600px; margin:60px auto;}
.row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #ECEAE4; font-size: 13px; }
.label { color: #928A83; }
.value { font-weight: 600; }
.note { margin-top: 24px; font-size: 12px; color: #928A83; text-align: center; }
</style></head><body>
<div class="card">
  <h1>{{ code }}</h1>
  <div class="sub">{{ subject }}</div>
  <div class="row"><span class="label">Language</span><span class="value">{{ lang|upper }}</span></div>
  <div class="row"><span class="label">Status</span><span class="value">{{ status }}</span></div>
  <div class="row"><span class="label">Total</span><span class="value">{{ currency }} {{ grand_total }}</span></div>
  <div class="note">Full document is being prepared. Please check back later.</div>
</div>
</body></html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
