# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-04-24

### Added — material + drawing submission workflow
- **Templates:** `docs/reports/drawing-submission-template.html` (clone of material template
  with drawing-specific fields: Discipline, Issue Purpose, Drawn By, Checked By;
  Drawing List table with Drawing No / Title / Rev / Scale / Sheet Size;
  attachments list for PDFs / CAD / model / calcs).
- **Firestore:** new `submissions` collection (database `go-documents`). Doc id
  scheme `MS-<SO>-NNN` / `DS-<SO>-NNN`. See `src/firestore_submissions.py` for
  models, id generation, CRUD, and `list_so_refs()` dashboard aggregation.
- **App endpoints (`src/app.py`):**
  - `POST /api/submissions` — create a material or drawing submission
  - `POST /api/submissions/<id>/attachments` — upload file → GCS
    `go-documents-files/submissions/<id>/attachments/<filename>`
  - `POST /api/submissions/<id>/send` — render PDF, fetch recipients via
    `project_email_loops.get_recipients(soRef)`, send via Gmail as
    `eukrit@goco.bz` (DWD), apply Submissions label, publish Pub/Sub event
  - `PATCH /api/submissions/<id>/status` — update approval status
  - `GET /submissions/<id>` — view filled HTML · `/submissions/<id>/pdf` — PDF
  - `GET /dashboard` — master project directory (all SO refs with counts)
  - `GET /projects/<soRef>` — per-project submission dashboard
  - `POST /pubsub/push` — Pub/Sub push receiver → Slack fan-out
- **Gmail:** `src/gmail_sender.py` — DWD-impersonated send as `eukrit@goco.bz`,
  applies `Submissions/Materials` or `Submissions/Drawings` label on the sent
  message via `messages.modify` (filters can't reliably match outgoing).
- **PDF render:** `src/submission_render.py` — WeasyPrint-based server-side PDF
  render from the HTML templates (no headless Chromium).
- **Events:** `src/submission_events.py` publishes to Pub/Sub topic
  `submission-events` on created/sent/status_changed. `src/slack_notifier.py`
  posts to `#submission-materials` / `#submission-drawings` with an Open button
  linking back to `/submissions/<id>`.
- **Setup scripts:**
  - `scripts/setup_gmail_labels.py` — create `Submissions/Materials` and
    `Submissions/Drawings` labels on eukrit@goco.bz
  - `scripts/setup_pubsub.sh` — create topic + push subscription to Cloud Run
    `/pubsub/push`, wire SA as invoker
  - `scripts/setup_slack_channels.py` — create `#submission-materials` and
    `#submission-drawings` public channels
- **Deploy:** Dockerfile bumped to install Pango/HarfBuzz/libjpeg for
  WeasyPrint; Cloud Run memory raised to 1Gi, env vars `GCP_PROJECT`,
  `SUBMISSION_SENDER`, `SUBMISSION_EVENTS_TOPIC` set.

### Changed
- `src/app.py` — root `/` now redirects to `/dashboard`; submission viewer
  prefers new `submissions` collection, falls back to legacy `document-records`.

### Prerequisites (must be done once by owner)
- Grant DWD on `claude@ai-agents-go` SA for scopes `gmail.send`,
  `gmail.modify`, `gmail.labels` (Workspace admin console).
- `scripts/setup_pubsub.sh` must run after first Cloud Run deploy so the push
  URL resolves.

## [1.1.0] - 2026-04-22

### Added — project email-loop lookup
- `src/project_email_loops.py` — reads `go_project_email_loops` collection
  from the `go-sales-orders` Firestore database at document-submission time.
  Exposes `get_loop(so_ref)` (full doc) and `get_recipients(so_ref, *,
  internal_only, external_only, min_confidence)` (flat to/cc/bcc email lists)
  with `min_confidence` defaulting to `MEDIUM` so LOW-confidence Gmail
  backfill rows are excluded from real sends.
- Collection schema and population scripts live in the `go-sales-orders`
  project: `create_email_loops_collection.py` (manual) and
  `backfill_email_loops.py` (Gmail-driven).

## [1.0.0] - 2026-04-08

### Added
- Firestore database `go-documents` (asia-southeast1)
- `document-templates` collection with `areda-quotation` template schema
- `document-records` collection (migrated from `areda_quotations`)
- `document_counters` collection for running number generation
- AQ-26001: ED 70 Aluminum Folding Door quotation (EN + TH)
- AQ-26002: OPK Multi-Panel Folding Wooden Door Hardware System quotation (EN + TH)
- Quotation HTML templates (EN + TH) with Areda design system
- Pydantic models for document records (`src/firestore_models.py`)
- Firestore CRUD + running number generation (`src/firestore_quotations.py`)
- China-Thai freight calculator (Gift Somlak confirmed rates)
- Migration script from `areda-product-catalogs` DB to `go-documents` DB
- Product images extracted from OPK supplier Excel
- CI/CD infra from goco-project-template (Dockerfile, cloudbuild, scripts)
- GitHub repo: `eukrit/go-documents`

## [0.1.0] - 2026-03-24

### Added
- Initial project template with CI/CD pipeline
