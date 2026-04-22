# Changelog

All notable changes to this project will be documented in this file.

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
