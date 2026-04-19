"""GO Documents — Document serving app.

Serves generated documents at:
  https://docs.aredaatelier.com/<type>/<doc_id>  (Areda-branded documents)
  https://docs.leka.studio/<type>/<doc_id>       (all other documents)

Document types: quotations, submissions, datasheets, certificates, sales-sheets

All pages are noindex/nofollow — not intended for public search.
"""

import os

from flask import Flask, Response, abort, redirect, render_template_string, request
from google.cloud import firestore, storage

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
    "material-approvals": "material-approval",
}

# Brand routing: template_id prefix -> canonical domain
BRAND_DOMAINS = {
    "areda": "docs.aredaatelier.com",
}
DEFAULT_DOMAIN = "docs.leka.studio"

NOINDEX_HEADERS = {
    "X-Robots-Tag": "noindex, nofollow, noarchive, nosnippet",
    "Cache-Control": "private, no-store",
}


def get_db():
    if not hasattr(get_db, "_client"):
        get_db._client = firestore.Client(database=DATABASE)
    return get_db._client


# ---------- robots.txt ----------

@app.route("/robots.txt")
def robots():
    return Response(
        "User-agent: *\nDisallow: /\n",
        mimetype="text/plain",
        headers=NOINDEX_HEADERS,
    )


# ---------- Health check ----------

@app.route("/")
def index():
    return Response("GO Documents", headers=NOINDEX_HEADERS)


@app.route("/healthz")
def healthz():
    return "ok"


# ---------- Document list by type ----------

@app.route("/<doc_type_path>")
def list_documents(doc_type_path):
    doc_type = VALID_TYPES.get(doc_type_path)
    if not doc_type:
        abort(404)

    db = get_db()
    docs = (
        db.collection(COLLECTION)
        .where("document_type", "==", doc_type)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(100)
        .stream()
    )

    items = []
    for doc in docs:
        d = doc.to_dict()
        items.append({
            "id": doc.id,
            "code": d.get("quotation_code", doc.id),
            "subject": d.get("subject", ""),
            "language": d.get("language", ""),
            "status": d.get("status", ""),
            "date": str(d.get("document_date", ""))[:10],
            "url": f"/{doc_type_path}/{doc.id}",
        })

    html = render_template_string(LIST_TEMPLATE, doc_type=doc_type_path, items=items)
    return Response(html, headers=NOINDEX_HEADERS)


# ---------- Redirect helper ----------

def _get_canonical_domain(template_id: str) -> str:
    """Return the canonical domain for a template."""
    for brand_prefix, brand_domain in BRAND_DOMAINS.items():
        if template_id.startswith(brand_prefix):
            return brand_domain
    return DEFAULT_DOMAIN


def _maybe_redirect(data: dict, doc_type_path: str, doc_id: str):
    """301 redirect if the request is on the wrong domain for this document."""
    template_id = data.get("template_id", "")
    canonical = _get_canonical_domain(template_id)
    current_host = request.host.split(":")[0]
    if current_host != canonical:
        return redirect(
            f"https://{canonical}/{doc_type_path}/{doc_id}", code=301
        )
    return None


# ---------- Serve single document ----------

@app.route("/<doc_type_path>/<doc_id>")
def serve_document(doc_type_path, doc_id):
    doc_type = VALID_TYPES.get(doc_type_path)
    if not doc_type:
        abort(404)

    db = get_db()
    doc_ref = db.collection(COLLECTION).document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        abort(404)

    data = doc.to_dict()
    if data.get("document_type") != doc_type:
        abort(404)

    # Redirect to canonical domain if needed
    redir = _maybe_redirect(data, doc_type_path, doc_id)
    if redir:
        return redir

    # Check for generated HTML in GCS
    gcs_html_path = data.get("generated_html_gcs")
    if gcs_html_path:
        try:
            client = storage.Client()
            bucket = client.bucket(GCS_BUCKET)
            blob = bucket.blob(gcs_html_path)
            html = blob.download_as_text()
            return Response(html, content_type="text/html", headers=NOINDEX_HEADERS)
        except Exception:
            pass

    # Check for inline HTML content
    html_content = data.get("html_content")
    if html_content:
        return Response(html_content, content_type="text/html", headers=NOINDEX_HEADERS)

    # Fallback: render a metadata page
    code = data.get("quotation_code", doc_id)
    lang = data.get("language", "en")
    subject = data.get("subject", "")
    status = data.get("status", "draft")
    grand_total = data.get("grand_total", 0)
    currency = data.get("currency", "THB")

    html = render_template_string(
        DOC_FALLBACK_TEMPLATE,
        code=code,
        lang=lang,
        subject=subject,
        status=status,
        grand_total=f"{grand_total:,.2f}",
        currency=currency,
        doc_type=doc_type_path,
        doc_id=doc_id,
    )
    return Response(html, content_type="text/html", headers=NOINDEX_HEADERS)


# ---------- Templates ----------

LIST_TEMPLATE = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="robots" content="noindex, nofollow">
<title>GO Documents — {{ doc_type }}</title>
<style>
  body { font-family: 'Manrope', system-ui, sans-serif; margin: 40px; color: #252828; background: #F5F4F0; }
  h1 { font-size: 24px; text-transform: capitalize; margin-bottom: 24px; }
  table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  th { background: #252828; color: #E1DFD4; text-align: left; padding: 10px 16px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; }
  td { padding: 10px 16px; border-bottom: 1px solid #ECEAE4; font-size: 13px; }
  a { color: #252828; text-decoration: none; font-weight: 600; }
  a:hover { text-decoration: underline; }
  .status { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
  .status-draft { background: #FEF3C7; color: #92400E; }
  .status-sent { background: #DBEAFE; color: #1E40AF; }
  .status-accepted { background: #D1FAE5; color: #065F46; }
  .empty { text-align: center; padding: 40px; color: #928A83; }
</style>
</head><body>
<h1>{{ doc_type }}</h1>
{% if items %}
<table>
<thead><tr><th>Code</th><th>Subject</th><th>Lang</th><th>Date</th><th>Status</th></tr></thead>
<tbody>
{% for item in items %}
<tr>
  <td><a href="{{ item.url }}">{{ item.code }}</a></td>
  <td>{{ item.subject }}</td>
  <td>{{ item.language|upper }}</td>
  <td>{{ item.date }}</td>
  <td><span class="status status-{{ item.status }}">{{ item.status }}</span></td>
</tr>
{% endfor %}
</tbody>
</table>
{% else %}
<div class="empty">No {{ doc_type }} found.</div>
{% endif %}
</body></html>"""

DOC_FALLBACK_TEMPLATE = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="robots" content="noindex, nofollow">
<title>{{ code }} — GO Documents</title>
<style>
  body { font-family: 'Manrope', system-ui, sans-serif; margin: 60px auto; max-width: 600px; color: #252828; }
  .card { background: white; padding: 32px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  h1 { font-size: 22px; margin-bottom: 8px; }
  .subject { color: #928A83; font-size: 14px; margin-bottom: 24px; }
  .row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #ECEAE4; font-size: 13px; }
  .label { color: #928A83; }
  .value { font-weight: 600; }
  .note { margin-top: 24px; font-size: 12px; color: #928A83; text-align: center; }
</style>
</head><body>
<div class="card">
  <h1>{{ code }}</h1>
  <div class="subject">{{ subject }}</div>
  <div class="row"><span class="label">Language</span><span class="value">{{ lang|upper }}</span></div>
  <div class="row"><span class="label">Status</span><span class="value">{{ status }}</span></div>
  <div class="row"><span class="label">Total</span><span class="value">{{ currency }} {{ grand_total }}</span></div>
  <div class="note">Full document is being prepared. Please check back later.</div>
</div>
</body></html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
