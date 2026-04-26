# Changelog

All notable changes to this project will be documented in this file.

## [1.3.2] - 2026-04-26

### Changed — Drive folder ID + Slack signing secret auto-load

- `src/drive_upload.py` — switched from name-resolution ("GO Submissions"
  Shared Drive lookup) to a hardcoded Drive folder ID with env override.
  Default points at the **"Submissions GO"** folder Eukrit pre-created
  (`1gAhGAI94Z96aFUm3nCp66QO573ixm-Vh`). Override via
  `SUBMISSIONS_DRIVE_FOLDER_ID` env. Works for both Shared Drive subfolders
  and My Drive folders via `corpora=allDrives` + `supportsAllDrives=True`.
- `src/app.py` — `_verify_slack_signature` now falls back to Secret Manager
  (`slack-signing-secret` in `ai-agents-go`) when `SLACK_SIGNING_SECRET` env
  is unset. Same pattern as `slack_notifier._get_token()` for the bot token.
  Cached in-process. Override secret name via `SLACK_SIGNING_SECRET_NAME`.

### Operations checklist (replaces v1.3.1 manual env-var step)
- ~~Set `SLACK_SIGNING_SECRET` env on go-documents Cloud Run~~ — no longer
  required; auto-loaded from `slack-signing-secret` GSM secret. Verify the
  go-documents runtime SA has `roles/secretmanager.secretAccessor` on it.
- DWD scope `drive.file` still required for `claude@ai-agents-go`.
- `eukrit@goco.bz` (the impersonated user) needs Editor access on the
  "Submissions GO" folder. Since Eukrit created it, this is already the case.

## [1.3.1] - 2026-04-26

### Changed — Slack Router wiring corrected

The "Slack Router" in `data-communications/slack-router/` is the **incoming
interactivity dispatcher**, not an outgoing channel-resolver. v1.3.0 wired
`slack_notifier.py` to a non-existent `route_event` HTTP endpoint based on a
misread of upstream. v1.3.1 corrects this:

- `src/slack_notifier.py` restored to hardcoded channel posting (legacy
  behaviour) but the card now carries **interactive Approve / Reject /
  Comment buttons** with `submission_*` `action_id` prefixes.
- New `/slack/interactivity` endpoint in `src/app.py` — receives button
  clicks forwarded by the slack-router service, verifies Slack signature
  via `SLACK_SIGNING_SECRET`, dispatches `submission_approve_*` /
  `submission_reject_*` / `submission_comment_*` to update the submission
  status and publish a `status_changed` Pub/Sub event (which fans out to
  Slack again as a status-update card).
- `data-communications/slack-router/routes.json` — new rule routing
  `submission_*` action_id prefix to `https://docs.leka.studio/slack/interactivity`.
- `data-communications/src/routing_engine.py` — added `submission_material` /
  `submission_drawing` to `_FALLBACK_SUBCATEGORY_MAP` so organic email
  classification (e.g. consultant replies referencing a submission) lands in
  the right channel without Firestore config bootstrap.

### Operations checklist (additions to v1.3.0)
- Set `SLACK_SIGNING_SECRET` env on go-documents Cloud Run (same secret as
  slack-router uses; from the GoCo Slack app config).
- Redeploy `slack-router` Cloud Run service to pick up the new
  `routes.json`. (Existing Slack app interactivity URL is already pointed
  at slack-router — no Slack-app-config change needed.)

## [1.3.0] - 2026-04-26

### Added — submission sign-off (clause + Drive eSignature)

- **Bilingual "Acceptance & Response Period" clause** (EN + TH) appended to every
  submission PDF AND every submission email body. Default 7 working days,
  configurable via `SUBMISSION_RESPONSE_DAYS` env var. If no written comments are
  received in that window, the submission is deemed accepted in full.
  Single source of truth: `src/submission_clause.py`.
- **Templates:** new `<!-- ACCEPTANCE_CLAUSE -->` marker + `.limitations.acceptance`
  styling in both `docs/reports/material-submission-template.html` and
  `docs/reports/drawing-submission-template.html`.
- **Email injection:** `gmail_sender.send_submission_email` now appends the clause
  to default and override `body_text`. Opt-out via `include_acceptance_clause=False`.
- **Google Drive eSignature workflow:** new `src/drive_upload.py` mirrors every
  rendered PDF to Shared Drive `GO Submissions/Submissions/<soRef>/<sid>.pdf` via
  DWD impersonation. `driveFileId` + `driveWebViewLink` persisted on the
  submission record. PMs click "Request signature" in Drive UI for native
  Workspace eSignature. (No public API yet — manual step.)
- **Slack notification card** carries Open + Drive (Sign) URL buttons
  (status-page + Drive web-view link). v1.3.1 adds Approve / Reject /
  Comment buttons routed via slack-router (see v1.3.1 entry above).

### Changed
- `src/submission_render.py` — `TEMPLATES` now reads from `docs/reports/`
  (Rule 13 docs-only layout) instead of repo root.
- `src/firestore_submissions.mark_sent()` — accepts `drive_file_id` /
  `drive_web_view_link`.

### Operations checklist (manual, post-deploy)
- Create Shared Drive **"GO Submissions"** in Workspace; add
  `claude@ai-agents-go.iam.gserviceaccount.com` as Content Manager.
- Grant DWD scope `https://www.googleapis.com/auth/drive.file` to
  `claude@ai-agents-go` in Workspace admin (existing scopes:
  `gmail.send`, `gmail.modify`, `gmail.labels`).
- Create Secret Manager secret `data-comms-router-token` with a random 32-byte
  value; grant `roles/secretmanager.secretAccessor` to the data-communications
  AND go-documents runtime SAs.
- Deploy data-communications: `gcloud functions deploy route_event ...`.
- Update go-documents Cloud Run service env: set `SLACK_ROUTER_URL` to the
  deployed function URL.

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
