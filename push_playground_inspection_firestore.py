"""Push playground inspection template and SO25-023 record to Firestore.

Database: go-documents (asia-southeast1)
Collections: document-templates, document-records
"""

import os
import sys
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
    "ai-agents-go-0d28f3991b7b.json",
)
if os.path.exists(CREDS_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDS_PATH


def get_db() -> firestore.Client:
    return firestore.Client(database=DATABASE)


def push_template(db: firestore.Client) -> None:
    """Push the leka-playground-inspection template to document-templates."""
    template_id = "leka-playground-inspection"
    doc_ref = db.collection(TEMPLATES_COLLECTION).document(template_id)

    template_data = {
        "template_id": template_id,
        "document_type": "playground_inspection",
        "brand": "Leka Studio",
        "division": "Playground Safety Division",
        "title": "Playground Safety Inspection Certificate",
        "revision": "R1",
        "code_format": "SO{YY}-{NNN}",
        "code_prefix": "SO",
        "language": "en",
        "template_file": "playground-inspection-template.html",
        "design_system": {
            "font": "Manrope",
            "colors": {
                "navy": "#182557",
                "purple": "#8003FF",
                "cream": "#FFF9E6",
                "magenta": "#970260",
                "amber": "#FFA900",
                "red_orange": "#E54822",
            },
            "page_size": "A4",
            "orientation": "portrait",
        },
        "fields": {
            "report_no": {"type": "string", "required": True, "label": "Certificate / Report No."},
            "inspection_date": {"type": "date", "required": True, "label": "Inspection Date"},
            "playground_name": {"type": "string", "required": True, "label": "Playground Name"},
            "inspection_type": {"type": "string", "default": "Comprehensive Safety Inspection"},
            "site_location": {"type": "string", "required": True, "label": "Site Location"},
            "site_location_short": {"type": "string", "label": "Short Location (Page 2)"},
            "reinspection_date": {"type": "string", "label": "Recommended Reinspection Date"},
            "owner_operator": {"type": "string", "required": True, "label": "Owner / Operator"},
            "age_group": {"type": "string", "required": True, "label": "Intended User Age Group"},
            "warranty_start": {"type": "date", "label": "Warranty Start (= Handover Date)"},
            "warranty_end": {"type": "date", "label": "Warranty End"},
            "warranty_months": {"type": "number", "default": 12},
            "compliance_result": {"type": "enum", "options": ["substantial_compliance", "corrective_action"]},
            "inspector_name": {"type": "string", "default": "Eukrit Kraikosol"},
            "cpsi_cert_no": {"type": "string", "default": "64835-0801"},
            "cpsi_expiration": {"type": "string", "default": "08/01/2028"},
            "inspector_credential": {"type": "string", "default": "NRPA Certified Playground Safety Inspector (CPSI)"},
        },
        "inspector_defaults": {
            "name": "Eukrit Kraikosol",
            "credential": "NRPA Certified Playground Safety Inspector (CPSI)",
            "cpsi_cert_no": "64835-0801",
            "cpsi_expiration": "08/01/2028",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    doc_ref.set(template_data)
    print(f"[OK] Template pushed: document-templates/{template_id}")


def push_so25_023_record(db: firestore.Client) -> None:
    """Push the SO25-023 inspection record to document-records."""
    record_data = {
        "document_type": "playground_inspection",
        "template_id": "leka-playground-inspection",
        "report_no": "SO25-023",
        "revision_no": 1,
        "revision_label": "R1",
        "status": "issued",
        "language": "en",

        # Site
        "site": {
            "playground_name": "Polo Club Playground",
            "site_location": "The Royal Bangkok Sports Club (RBSC Polo Club), 18 Soi Polo, Wireless Road, Lumpini, Pathumwan, Bangkok 10330",
            "site_location_short": "RBSC Polo Club, 18 Soi Polo, Wireless Road, Lumpini, Pathumwan, Bangkok 10330",
            "owner_operator": "The Royal Bangkok Sports Club (RBSC Polo Club)",
            "age_group": "5 – 12 Years Old",
        },

        # Client
        "client": {
            "attn": "Worawuth Kraitong",
            "company": "The Royal Bangkok Sports Club (RBSC Polo Club)",
            "email": "worawuth.k@rbsc.org",
            "tel": "",
        },

        # Inspection
        "inspection_date": "2026-03-12T00:00:00Z",
        "inspection_type": "Comprehensive Safety Inspection",
        "reinspection_date": "March 2027",
        "compliance_result": "substantial_compliance",

        # Warranty (R1)
        "warranty": {
            "handover_date": "2026-03-12T00:00:00Z",
            "warranty_months": 12,
            "warranty_start": "March 12, 2026",
            "warranty_end": "March 12, 2027",
        },

        # Inspector
        "inspector": {
            "name": "Eukrit Kraikosol",
            "credential": "NRPA Certified Playground Safety Inspector (CPSI)",
            "cpsi_cert_no": "64835-0801",
            "cpsi_expiration": "08/01/2028",
        },

        # Dates
        "document_date": "2026-03-12T00:00:00Z",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "issued_at": datetime.now(timezone.utc).isoformat(),

        # Audit
        "created_by": "eukrit@goco.bz",
        "updated_by": "eukrit@goco.bz",
        "notes": "First playground inspection certificate issued under Leka Studio Playground Safety Division.",
    }

    # Use report_no as document ID for easy lookup
    doc_ref = db.collection(RECORDS_COLLECTION).document("SO25-023")
    doc_ref.set(record_data)
    print(f"[OK] Record pushed: document-records/SO25-023")


def push_counter(db: firestore.Client) -> None:
    """Set the inspection counter to 23 (SO25-023 is the latest)."""
    counter_ref = db.collection(COUNTERS_COLLECTION).document("inspection-2025")
    counter_ref.set({
        "document_type": "playground_inspection",
        "prefix": "SO",
        "year": 2025,
        "last_number": 23,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    print("[OK] Counter set: document_counters/inspection-2025 -> last_number=23")


def main():
    db = get_db()
    print(f"Connected to Firestore database: {DATABASE}\n")

    push_template(db)
    push_so25_023_record(db)
    push_counter(db)

    print("\nAll done!")


if __name__ == "__main__":
    main()
