# GO Documents

Centralized document generation system for GO Corporation. Generates professional quotations, invoices, and other business documents in English and Thai with Firestore-backed storage.

## Architecture

```
go-documents/
  src/
    firestore_models.py              # Pydantic models for quotations
    firestore_quotations.py          # CRUD + running number for quotations
    firestore_inspection_models.py   # Pydantic models for inspection certificates
    firestore_inspections.py         # CRUD + running number for inspections
  docs/reports/quotation-template.html            # EN quotation HTML template (Areda design system)
  docs/reports/quotation-template-th.html         # TH quotation HTML template
  docs/reports/playground-inspection-template.html # Playground inspection cert (Leka design system, Rev R1)
  AQ-*-*.html                        # Generated quotation files (EN + TH)
  freight_calculator.py              # China-Thai landed cost calculator
  agents/china-thai/                 # Freight calculation agent (Gift Somlak rates)
  images/                            # Logo + product images
```

## Firestore Database

| Property | Value |
|---|---|
| Database | `go-documents` |
| Region | `asia-southeast1` |
| GCP Project | `ai-agents-go` |
| Type | Firestore Native |

### Collections

| Collection | Purpose |
|---|---|
| `document-templates` | Template schemas (field definitions, defaults, payment splits) |
| `document-records` | All generated documents — quotations, invoices, POs, etc. |
| `document_counters` | Running number counters per document type per year |

### document-templates

Each template defines the schema, defaults, and payment splits for a document type.

| Document ID | Template | Code Format |
|---|---|---|
| `areda-quotation` | Areda Atelier Quotation | `AQ-{YY}{NNN}` |
| `leka-playground-inspection` | Leka Studio Playground Safety Inspection Certificate | `SO{YY}-{NNN}` |

### document-records

All generated documents live here, distinguished by `document_type` field.

| Field | Description |
|---|---|
| `document_type` | `quotation`, `invoice`, `purchase_order`, etc. |
| `template_id` | References `document-templates/{id}` |
| `quotation_code` | Running code (AQ-26001, AQ-26002, ...) |
| `language` | `en` or `th` |
| `status` | `draft`, `sent`, `accepted`, `rejected`, `expired` |

### document_counters

| Document ID | Format | Example |
|---|---|---|
| `quotation-2026` | `{type}-{year}` | Tracks last quotation number for 2026 |
| `inspection-2025` | `{type}-{year}` | Tracks last inspection number for 2025 |

## Quotation Templates

### Design System
- Brand: Areda Atelier (by GO Corporation)
- Font: Manrope (EN) + Noto Sans Thai (TH)
- A4 portrait, print-optimized
- Color tokens: charcoal `#252828`, cream `#E1DFD4`, taupe `#928A83`

### Template Features
- Company header with logo
- Customer + document info grid
- Product specification box
- Product reference image gallery
- Line items table with section headers
- Totals block (subtotal, VAT 7%, grand total)
- Estimated schedule (duration-based, no fixed dates)
- Scope of supply / terms & conditions
- Payment terms table (configurable splits)
- Signature block + footer

### Payment Splits
- **Supply only** (default for imported goods): 50% deposit / 40% before shipment / 10% on delivery
- **Supply + install**: 30% deposit / 30% before shipment / 30% on delivery / 10% after handover

## Freight Calculator

China-Thai landed cost calculator using confirmed rates:

| Rate | Source | Value |
|---|---|---|
| Sea LCL (CBM) | Gift Somlak rate card | THB 4,600/CBM |
| Sea LCL (KGS) | Gift Somlak rate card | THB 35/KG |
| Land (CBM) | Gift Somlak rate card | THB 7,200/CBM |
| Insurance | Chubb via Logimark | 0.45% of CIF x 110%, min USD 40 |
| Clearance fee | Forwarder | ~THB 3,000 |
| Last-mile | Bangkok delivery | THB 1,500-3,500 |

Billing rule: `max(CBM-based, KGS-based)` — standard LCL practice.

## Usage

### Create a new quotation

1. Prepare supplier data (PI, pricing, specs)
2. Run freight calculator to determine landed cost and margin
3. Create HTML from template (EN + TH)
4. Push to Firestore:

```python
from src.firestore_quotations import create_quotation
from src.firestore_models import CustomerInfo, ProposerInfo, LineItem

doc_id, quotation = create_quotation(
    customer=CustomerInfo(company="Acme Co.", ...),
    project_name="Villa Project",
    subject="Folding Door Hardware",
    proposed_by=ProposerInfo(name="Sales Rep", ...),
    items=[LineItem(item_no=1, product_code="AA-HW-FD01", ...)],
    language="en",
)
```

### Generate PDF

```bash
# Edge (Windows)
msedge --headless --print-to-pdf="output.pdf" --print-to-pdf-no-header --no-margins "file:///path/to/quotation.html"

# Chrome (Mac/Linux)
google-chrome --headless --print-to-pdf="output.pdf" --print-to-pdf-no-header --no-margins "file:///path/to/quotation.html"
```

## Credentials

- GCP service account: `claude@ai-agents-go.iam.gserviceaccount.com`
- Key file: stored in `Credentials Claude Code/` folder (never committed)
- Set `GOOGLE_APPLICATION_CREDENTIALS` env var or use `.env`

## GCP Setup
- Project: `ai-agents-go` (538978391890)
- Region: `asia-southeast1`
- Service account: `claude@ai-agents-go.iam.gserviceaccount.com`

## Related Repos

| Repo | Purpose |
|---|---|
| `eukrit/business-automation` | ERP gateway, shared libs, dashboard |
| `eukrit/accounting-automation` | Peak API, Xero, MCP server |
| `eukrit/procurement-automation` | RFQ workflows, vendor sourcing |

## Playground Inspection Certificates

### Design System
- Brand: Leka Studio — Playground Safety Division
- Font: Manrope
- A4 portrait, print-optimized (2-page: full cert + short form)
- Color tokens: navy `#182557`, purple `#8003FF`, cream `#FFF9E6`, magenta `#970260`

### Template Features
- Leka Studio header with SVG logo
- Gradient accent bars (top + bottom)
- Site information grid (8 fields)
- Warranty period field (R1 addition — 12 months from handover)
- Inspection scope + criteria referenced
- Summary statement with checkbox (Substantial Compliance / Corrective Action)
- Referenced documents list
- Inspector credentials block (CPSI)
- Signature row + limitations disclaimer
- Page 2: Short-form pass certificate

### Template Placeholders
| Placeholder | Description |
|---|---|
| `{{report_no}}` | Certificate / Report No. (SO25-023) |
| `{{inspection_date}}` | Inspection date (March 12, 2026) |
| `{{playground_name}}` | Playground name |
| `{{inspection_type}}` | Type of inspection |
| `{{site_location}}` | Full address |
| `{{site_location_short}}` | Short address (Page 2) |
| `{{reinspection_date}}` | Recommended reinspection |
| `{{owner_operator}}` | Owner / operator name |
| `{{age_group}}` | Intended user age group |
| `{{warranty_start}}` | Warranty start date |
| `{{warranty_end}}` | Warranty end date |
| `{{warranty_months}}` | Warranty duration |
| `{{inspector_name}}` | Inspector name |
| `{{cpsi_cert_no}}` | CPSI certificate number |
| `{{cpsi_expiration}}` | CPSI expiration date |
| `{{inspector_credential}}` | Full credential title |

### Existing Inspections

| Code | Playground | Client | Status |
|---|---|---|---|
| SO25-023 | Polo Club Playground | RBSC Polo Club (Worawuth Kraitong) | Issued — Substantial Compliance |

## Existing Quotations

| Code | Product | Supplier | Selling Price |
|---|---|---|---|
| AQ-26001 | ED 70 Aluminum Folding Door — Thermal Break, Double Glazed | Foshan | THB 99,000 |
| AQ-26002 | OPK Multi-Panel Folding Wooden Door Hardware System | Guangdong OPK | THB 19,500 |
