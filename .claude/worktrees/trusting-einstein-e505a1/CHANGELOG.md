# Changelog

All notable changes to this project will be documented in this file.

## [1.5.0] - 2026-04-20

### Removed
- `tensile-technic-playground-inspection` template (both the Firestore doc and the local HTML). Playground inspections remain a Leka Studio offering only (`leka-playground-inspection`).

### Added
- New document type `shade-inspection` for Tensile Technic:
  - `src/firestore_shade_inspection_models.py` — Pydantic model (`ShadeInspectionCertificate`) with sub-models `SiteInfo`, `ClientInfo`, `InspectorInfo`, `FindingItem`, `SystemFindings`, `WarrantyBlock`; enums `ShadeInspectionStatus`, `InspectionScope`, `ComplianceResult`, `Severity`, `StructureType`.
  - `DocumentType.SHADE_INSPECTION = "shade-inspection"` + URL path `/shade-inspections/<doc_id>` (app.py + firestore_models.py).
  - `shade-inspection-template-tensile-technic.html` — A4 certificate with Tensile Technic design tokens, 6 inspection-system tables (Membrane / Seams / Tension Hardware / Structural / Drainage / Environmental), severity chips (OK / Advisory / Monitor / Action 30d / Immediate), compliance result banner, standards appendix, and signoff.
  - Code format: `TSI-{YY}-{NNN}` (e.g., `TSI-26-001`).
  - Firestore template doc `document-templates/tensile-technic-shade-inspection` published with standards list, default systems, severity levels, compliance results, and post-event wind threshold (80 km/h).

### Standards referenced on the template
- ASCE/SEI 55 — Tensile Membrane Structures (design, fabrication, installation, maintenance)
- NFPA 701 — Fire Tests for Flame Propagation of Textiles and Films
- ASTM D751 / D5034 / D4851 — Coated-fabric and mechanical test methods
- AS 2428 — Shade fabrics for commercial and domestic use (Australia)
- AS/NZS 1170 — Structural design actions (wind / load / seismic)
- EN 13782 — Temporary structures — tents — safety (Europe)
- IFAI / Tensile Membrane Association — Tensile Structures Maintenance Guide

### Research note
Serge Ferrari and IFAI public pages did not return structured inspection checklists (404 / redirect / empty search page). Template was built from my working knowledge of the above standards. Flag any items to revise against your internal engineering sign-off.

## [1.4.0] - 2026-04-20

### Added
- **Business Unit tagging** — every document and template in Firestore now carries a `business_unit` field (`Leka Studio` or `Tensile Technic`). Pydantic models updated in `src/firestore_models.py`, `src/firestore_inspection_models.py`, `src/firestore_material_approval_models.py`.
- `migrate_business_unit.py` — idempotent backfill; tags existing `document-templates` and `document-records` with `business_unit="Leka Studio"` when missing.
- `push_tensile_technic_templates.py` — registers 3 Tensile Technic templates in `document-templates`.
- `push_material_approvals_tensile_technic.py` — mirrors the Leka MA library under Tensile Technic: 50 records (`TT-26-001` Soltis 502 Proof fully enriched; `TT-26-002`..`TT-26-050` stubs mapping 1-to-1 with the 49 Leka stubs).
- Four Tensile Technic HTML templates (design tokens from Figma `HOwMIRipr2i6fH5ihbzhDz`):
  - `material-approval-template-tensile-technic.html`
  - `quotation-template-tensile-technic.html` (EN)
  - `quotation-template-tensile-technic-th.html` (TH)
  - `playground-inspection-template-tensile-technic.html`
- SOP updated ([docs/material-approval-SOP.md](docs/material-approval-SOP.md)) with a business-unit routing table.

### Firestore writes
- **Migration:** 56 records/templates tagged `business_unit="Leka Studio"` (53 records + 3 templates — Areda quotations and inspection also included per the explicit instruction to tag all as Leka Studio).
- **Tensile Technic templates:** `document-templates/tensile-technic-quotation`, `.../tensile-technic-playground-inspection`, `.../tensile-technic-material-approval`.
- **Tensile Technic material approvals:** `document-records/TT-26-001` … `TT-26-050` (50 records, `business_unit="Tensile Technic"`, all 50 Serge Ferrari PVC products).
- **Counter:** `document_counters/material-approval-2026-tensile-technic` → `last_number=50`.

### Design-system note
Figma file `HOwMIRipr2i6fH5ihbzhDz` was reachable via MCP, but Page 1 is an empty canvas and variable extraction requires an active node selection in the desktop app. The TT tokens shipped here (charcoal navy `#0F1B2E` + tension-orange `#D06B2A` + bone `#F3EEE5`, Inter + JetBrains Mono) are a reference palette distinct from Leka Studio. Sync with the Figma file when specific node IDs are provided.

## [1.3.0] - 2026-04-19

### Added
- `docs/material-approval-SOP.md` — end-to-end standard operating procedure (data gathering, HTML template, Firestore registration, bulk import, style rules, ship checklist).
- `data/material-approvals.seed.json` — source-of-truth seed for 49 PVC-coated Serge Ferrari products (Soltis, Tenseo, Stamoid, Flexlight, Batyline, Seemee Decolit). Explicitly PVC-free families excluded (Canatex, Eden Life, Biobrane).
- `push_material_approvals_bulk.py` — idempotent bulk importer; supports `--dry-run`; ensures the `leka-material-approval` template exists; advances the counter without regression.

### Firestore writes
- `document-records/MA26-002` … `document-records/MA26-050` (49 new material-approval stubs, status `draft`, project `Material Library`).
- `document_counters/material-approval-2026` advanced to `last_number=50`.

Each seeded record is a library stub — titles, family, URL, and category are authoritative; images/colors/datasheet facts are empty by design and must be enriched per the SOP before a project RFA is issued.

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
