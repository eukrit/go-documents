# Changelog

All notable changes to this project will be documented in this file.

## [1.2.2] - 2026-04-19

### Fixed
- `docs/materials/soltis-502-proof.html`: gallery card captions no longer clipped — image now lives in an `.img-wrap` with fixed 4:3 aspect-ratio while the caption flows below naturally (card height is content-driven, no more `overflow: hidden` truncation on the outer card).

### Changed
- Responsive breakpoints tuned for tablets/phones:
  - Palette: 6 → 5 (≤1040px) → 4 (≤900px) → 3 (≤640px) → 2 (≤480px) columns
  - Gallery: 3 → 2 (≤900px) → 1 (≤480px) columns
  - Hero / project / approvals grids stay 2-col on tablets (collapse to 1-col at ≤640px instead of 980px)
  - Material grid stacks at ≤900px
  - Tighter padding, smaller hero title, stacked footer on phones

## [1.2.1] - 2026-04-19

### Changed
- `docs/materials/soltis-502-proof.html` + `MA26-001` record: replaced placeholder/approximate palette with the official Serge Ferrari Soltis 502 Proof range (21 colors, manufacturer codes `502V3-xxxxC`)
- Gallery now uses 3 real Serge Ferrari product photos (shade sail, Treebones Resort lodge, Chaumont-sur-Loire festival)
- Hex values labeled as display approximations; manufacturer codes are authoritative

## [1.2.0] - 2026-04-19

### Added
- `material-approval` document type registered in `document-templates`, `document-records`, and `document_counters`
- `src/firestore_material_approval_models.py` — Pydantic models (`MaterialApproval`, `MaterialRecord`, `MaterialImage`, `ColorSwatch`, `ApprovalParty`)
- `push_material_approval_firestore.py` — seeds `leka-material-approval` template + `MA26-001` (Soltis 502 Proof) record
- `src/firestore_models.py`: `DocumentType.MATERIAL_APPROVAL` enum + `"material-approval": "material-approvals"` URL path
- `src/app.py`: `material-approvals` added to `VALID_TYPES` (serves at `/material-approvals/<doc_id>`)
- `docs/materials/soltis-502-proof.html`: added Pictures gallery + Color Palette section (8 reference swatches — White/Ivory/Sand/Grey/Anthracite/Black/Taupe/Brown)

### Firestore writes
- `document-templates/leka-material-approval`
- `document-records/MA26-001`
- `document_counters/material-approval-2026` (last_number=1)

## [1.1.0] - 2026-04-19

### Added
- `material-approval-template.html` — Leka Studio material approval template (Codex-built, Manrope + violet/navy design tokens)
- `docs/materials/soltis-502-proof.html` — filled Soltis 502 material submission example
- Source: imported from `2026 Leka Materal Approvals Codex`

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
