"""Push material-approval template and MA26-001 (Soltis 502 Proof) record to Firestore.

Database: go-documents (asia-southeast1)
Collections: document-templates, document-records, document_counters
Source: imported from 2026 Leka Materal Approvals Codex
"""

import os
from datetime import datetime, timezone

from google.cloud import firestore

# --- Config ---
DATABASE = "go-documents"
TEMPLATES_COLLECTION = "document-templates"
RECORDS_COLLECTION = "document-records"
COUNTERS_COLLECTION = "document_counters"

# Set credentials path
CREDS_PATH = os.path.join(
    os.path.expanduser("~"),
    "OneDrive", "Documents", "Claude Code",
    "Credentials Claude Code",
    "ai-agents-go-4c81b70995db.json",
)
if os.path.exists(CREDS_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDS_PATH


def get_db() -> firestore.Client:
    return firestore.Client(database=DATABASE)


def push_template(db: firestore.Client) -> None:
    """Push the leka-material-approval template to document-templates."""
    template_id = "leka-material-approval"
    doc_ref = db.collection(TEMPLATES_COLLECTION).document(template_id)

    template_data = {
        "template_id": template_id,
        "document_type": "material-approval",
        "brand": "Leka Studio",
        "division": "Design / Submissions",
        "title": "Request for Material Approval",
        "revision": "R1",
        "code_format": "MA{YY}-{NNN}",
        "code_prefix": "MA",
        "language": "en",
        "template_file": "material-approval-template.html",
        "example_file": "docs/materials/soltis-502-proof.html",
        "design_system": {
            "font": "Manrope",
            "colors": {
                "leka_navy": "#182557",
                "leka_cream": "#fff9e6",
                "leka_violet": "#8003ff",
                "leka_surface": "#f6f4ec",
                "leka_ink": "#20305f",
                "leka_muted": "#5f6888",
            },
            "page_size": "A4",
            "orientation": "portrait",
        },
        "fields": {
            "approval_code": {"type": "string", "required": True, "label": "Approval Code"},
            "document_ref": {"type": "string", "label": "Document Reference"},
            "title": {"type": "string", "required": True, "label": "Submission Title"},
            "issue_date": {"type": "date", "required": True, "label": "Issue Date"},
            "project_name": {"type": "string", "label": "Project"},
            "project_code": {"type": "string", "label": "Project Code (e.g., SO26-019)"},
            "client_owner": {"type": "string", "label": "Client / Owner"},
            "consultant_designer": {"type": "string", "label": "Consultant / Designer"},
            "materials": {
                "type": "array",
                "required": True,
                "label": "Materials",
                "item_shape": {
                    "material_name": "string",
                    "code": "string",
                    "description": "string",
                    "category": "string",
                    "main_application": "string",
                    "attachments": "array",
                    "images": "array",
                    "manufacturer_product_url": "string",
                },
            },
            "approvals": {
                "type": "array",
                "label": "Approval Routing",
                "item_shape": {
                    "role": "string",
                    "decision": "enum",
                    "signed_at": "date",
                },
            },
            "formal_note": {"type": "string", "label": "Formal Note"},
            "prepared_by": {"type": "string", "default": "GO Corporation Co., Ltd."},
        },
        "approval_roles_default": ["Consultant", "Designer", "Project Owner"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    doc_ref.set(template_data)
    print(f"[OK] Template pushed: document-templates/{template_id}")


def push_ma26_001_record(db: firestore.Client) -> None:
    """Push the Soltis 502 Proof material library entry as MA26-001."""
    record_data = {
        "document_type": "material-approval",
        "template_id": "leka-material-approval",
        "document_url": "https://docs.leka.studio/material-approvals/MA26-001",

        # Identity
        "approval_code": "MA26-001",
        "document_ref": "MAT-SOLTIS-502-PROOF",
        "revision_no": 0,
        "status": "submitted",
        "language": "en",
        "title": "Soltis 502 Proof",

        # Project (material library record — no specific project yet)
        "project": {
            "project_name": "Material Library",
            "project_code": "",
            "client_owner": "Internal material library record for future submissions.",
            "consultant_designer": "To be assigned per project submission.",
        },

        # Materials
        "materials": [
            {
                "material_name": "Soltis 502 Proof",
                "code": "502V3",
                "description": (
                    "Colorful, durable, waterproof membrane made with 100% recycled "
                    "polyester yarns. The datasheet highlights a satin finish, strong UV "
                    "durability, ease of upkeep, glare control, and reliable long-term "
                    "dimensional stability through Serge Ferrari's Précontraint technology."
                ),
                "category": "Fabric Membrane",
                "main_application": "Exterior solar protection, shade sails, and pergola roofs",
                "attachments": [
                    {
                        "name": "Soltis 502V3 Proof brochure card (8pp)",
                        "url": (
                            "file:///C:/Users/Eukrit/Downloads/"
                            "Soltis%20502V3%20Proof%20-%20new%20brochure%20card%20%288pp%29.pdf"
                        ),
                        "content_type": "application/pdf",
                    }
                ],
                "images": [
                    {
                        "url": "https://www.sergeferrari.com/app/uploads/Soltis-502-Proof-shade-sail-3-1920x1536.jpg",
                        "caption": "Tensioned shade sail application (Soltis 502 Proof).",
                        "role": "primary",
                        "credit": "Serge Ferrari",
                    },
                    {
                        "url": "https://www.sergeferrari.com/app/uploads/Lodge-by-Autonomous-Tent-Co.-at-Treebones-Resort-3-1-1920x1264.jpg",
                        "caption": "Lodge canopy — Autonomous Tent Co., Treebones Resort.",
                        "role": "gallery",
                        "credit": "Serge Ferrari",
                    },
                    {
                        "url": "https://www.sergeferrari.com/app/uploads/Festival-international-des-jardins-Chaumont-sur-Loire-4-1920x1440.jpg",
                        "caption": "Festival international des jardins, Chaumont-sur-Loire.",
                        "role": "gallery",
                        "credit": "Serge Ferrari",
                    },
                ],
                "colors": [
                    {"code": "502V3-51969C", "name": "White",        "hex": "#F5F3EC", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-51970C", "name": "Pearl White",  "hex": "#EAE4D6", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-51971C", "name": "Enamel White", "hex": "#F2EEDF", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-51979C", "name": "Champagne",    "hex": "#D7C9A8", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-50265C", "name": "Hemp",         "hex": "#C2B08C", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-51973C", "name": "Antelope",     "hex": "#A8825A", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-2171C",  "name": "Boulder",      "hex": "#A39A8C", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-2167C",  "name": "Concrete",     "hex": "#A7A29A", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-2168C",  "name": "Aluminium",    "hex": "#888A8C", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-51972C", "name": "Titanium",     "hex": "#6A6A68", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-1354C",  "name": "Anthracite",   "hex": "#3A3C40", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-8450C",  "name": "Black",        "hex": "#1A1A1A", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-50674C", "name": "Lemon",        "hex": "#E8D76A", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-2166C",  "name": "Buttercup",    "hex": "#E2C94E", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-51974C", "name": "Peach",        "hex": "#E8A585", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-8204C",  "name": "Orange",       "hex": "#E6762C", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-8255C",  "name": "Poppy",        "hex": "#D9422B", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-2012C",  "name": "Pepper",       "hex": "#B03A2E", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-50283C", "name": "Rust",         "hex": "#A94E1F", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-2150C",  "name": "Raspberry",    "hex": "#9B2743", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                    {"code": "502V3-8284C",  "name": "Burgundy",     "hex": "#5A1A25", "finish": "satin", "notes": "Display hex approximate; verify against physical sample."},
                ],
                "manufacturer_product_url": "https://www.sergeferrari.com/en/products/soltis/502-proof/",
                "composition": "100% recycled PET yarns with PVC coating.",
                "weight": "590 g/m²",
                "thickness": "0.45 mm",
                "roll_width": "180 cm",
                "use_cases": [
                    "Shade sails",
                    "Fixed pergola roofs",
                    "Retractable pergola roofs",
                ],
            }
        ],

        # Approval routing
        "approvals": [
            {"role": "Consultant", "decision": "pending"},
            {"role": "Designer", "decision": "pending"},
            {"role": "Project Owner", "decision": "pending"},
        ],

        # Submission metadata
        "prepared_by": "GO Corporation Co., Ltd.",
        "formal_note": (
            "Soltis 502 Proof is suitable as a waterproof fabric membrane for exterior "
            "solar protection. According to the brochure, its main applications include "
            "shade sails, fixed pergola roofs, and retractable pergola roofs. This material "
            "page can be reused as a starting point for future project-specific RFAs."
        ),
        "submission_notes": "",

        # Dates
        "issue_date": "2026-04-01T00:00:00Z",
        "document_date": "2026-04-01T00:00:00Z",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "submitted_at": datetime.now(timezone.utc).isoformat(),

        # Audit
        "created_by": "eukrit@goco.bz",
        "updated_by": "eukrit@goco.bz",
        "notes": "Seeded from 2026 Leka Materal Approvals Codex — Soltis 502 Proof material library entry.",
    }

    doc_ref = db.collection(RECORDS_COLLECTION).document("MA26-001")
    doc_ref.set(record_data)
    print("[OK] Record pushed: document-records/MA26-001")


def push_counter(db: firestore.Client) -> None:
    """Initialize the material-approval counter at 1 for 2026."""
    counter_ref = db.collection(COUNTERS_COLLECTION).document("material-approval-2026")
    counter_ref.set({
        "document_type": "material-approval",
        "prefix": "MA",
        "year": 2026,
        "last_number": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    print("[OK] Counter set: document_counters/material-approval-2026 -> last_number=1")


def main():
    db = get_db()
    print(f"Connected to Firestore database: {DATABASE}\n")

    push_template(db)
    push_ma26_001_record(db)
    push_counter(db)

    print("\nAll done!")


if __name__ == "__main__":
    main()
