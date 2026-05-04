"""Migrate areda_quotations to go-documents database.

1. Create document-templates collection with the quotation template schema
2. Copy areda_quotations from (default) DB to document-records in go-documents DB
3. Add document_type field to each record
"""

import os
from datetime import datetime, timezone

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    r"C:\Users\eukri\OneDrive\Documents\Claude Code"
    r"\Credentials Claude Code\ai-agents-go-9b4219be8c01.json"
)

from google.cloud import firestore


def utcnow():
    return datetime.now(timezone.utc)


# --- Template Schema ---

QUOTATION_TEMPLATE = {
    "template_id": "areda-quotation",
    "template_name": "Areda Atelier — Quotation",
    "template_name_th": "Areda Atelier — ใบเสนอราคา",
    "document_type": "quotation",
    "version": "1.0.0",
    "supported_languages": ["en", "th"],
    "description": "Customer-facing quotation for imported products (furniture, hardware, doors). "
                   "Includes product specs, line items, logistics, schedule, terms, and payment schedule.",
    "owner": "GO Corporation Co., Ltd.",
    "brand": "Areda Atelier",
    "html_templates": {
        "en": "quotation-template.html",
        "th": "quotation-template-th.html",
    },
    "code_prefix": "AQ",
    "code_format": "AQ-{YY}{NNN}",
    "counter_collection": "document_counters",
    "schema": {
        "identity": {
            "quotation_code": {"type": "string", "required": True, "description": "AQ-26001, AQ-26002, ..."},
            "revision_no": {"type": "integer", "default": 0},
            "status": {"type": "string", "enum": ["draft", "sent", "revised", "accepted", "rejected", "expired", "cancelled"], "default": "draft"},
            "language": {"type": "string", "enum": ["en", "th"], "default": "en"},
        },
        "customer": {
            "attn": {"type": "string"},
            "company": {"type": "string"},
            "address": {"type": "string"},
            "tax_id": {"type": "string"},
            "email": {"type": "string"},
            "tel": {"type": "string"},
        },
        "project": {
            "project_name": {"type": "string"},
            "subject": {"type": "string"},
        },
        "proposed_by": {
            "name": {"type": "string"},
            "email": {"type": "string"},
            "mobile": {"type": "string"},
        },
        "line_item": {
            "item_no": {"type": "integer", "required": True},
            "product_code": {"type": "string"},
            "description": {"type": "string"},
            "description_sub": {"type": "string"},
            "unit": {"type": "string"},
            "qty": {"type": "number", "default": 0},
            "unit_rate": {"type": "number", "default": 0},
            "amount": {"type": "number", "default": 0},
            "category": {"type": "string"},
            "vendor": {"type": "string"},
            "notes": {"type": "string"},
        },
        "financials": {
            "currency": {"type": "string", "enum": ["THB", "USD", "EUR", "CNY", "GBP"], "default": "THB"},
            "fx_rate": {"type": "number", "default": 1.0},
            "fx_base_currency": {"type": "string", "default": "THB"},
            "subtotal": {"type": "number"},
            "vat_rate": {"type": "number", "default": 7.0},
            "vat_amount": {"type": "number"},
            "grand_total": {"type": "number"},
            "discount_amount": {"type": "number", "default": 0},
            "discount_note": {"type": "string"},
        },
        "schedule_milestone": {
            "name": {"type": "string"},
            "duration_text": {"type": "string"},
            "target_date": {"type": "timestamp", "nullable": True},
            "actual_date": {"type": "timestamp", "nullable": True},
            "notes": {"type": "string"},
        },
        "payment_term": {
            "payment_no": {"type": "integer"},
            "percentage": {"type": "number"},
            "milestone": {"type": "string"},
            "amount": {"type": "number"},
            "status": {"type": "string", "enum": ["pending", "invoiced", "paid"], "default": "pending"},
            "due_date": {"type": "timestamp", "nullable": True},
            "paid_date": {"type": "timestamp", "nullable": True},
            "invoice_no": {"type": "string"},
        },
        "validity": {
            "valid_days": {"type": "integer", "default": 15},
            "valid_until": {"type": "timestamp", "nullable": True},
        },
        "dates": {
            "document_date": {"type": "timestamp"},
            "created_at": {"type": "timestamp"},
            "updated_at": {"type": "timestamp"},
            "sent_at": {"type": "timestamp", "nullable": True},
            "accepted_at": {"type": "timestamp", "nullable": True},
            "expired_at": {"type": "timestamp", "nullable": True},
        },
        "audit": {
            "created_by": {"type": "string"},
            "updated_by": {"type": "string"},
            "revision_history": {"type": "array"},
            "notes": {"type": "string"},
        },
    },
    "default_payment_splits": {
        "supply_only": [
            {"payment_no": 1, "percentage": 50, "milestone_en": "Deposit upon signing contract / order confirmation", "milestone_th": "มัดจำเมื่อลงนามสัญญา / ยืนยันคำสั่งซื้อ"},
            {"payment_no": 2, "percentage": 40, "milestone_en": "Before goods depart origin factory", "milestone_th": "ก่อนสินค้าออกจากโรงงานต้นทาง"},
            {"payment_no": 3, "percentage": 10, "milestone_en": "Upon delivery to site and goods receipt confirmation", "milestone_th": "เมื่อส่งมอบถึงหน้างานและยืนยันรับสินค้า"},
        ],
        "supply_and_install": [
            {"payment_no": 1, "percentage": 30, "milestone_en": "Deposit upon signing contract", "milestone_th": "มัดจำเมื่อลงนามสัญญา"},
            {"payment_no": 2, "percentage": 30, "milestone_en": "Before shipment from origin", "milestone_th": "ก่อนจัดส่งจากต้นทาง"},
            {"payment_no": 3, "percentage": 30, "milestone_en": "Upon delivery to site", "milestone_th": "เมื่อส่งมอบถึงหน้างาน"},
            {"payment_no": 4, "percentage": 10, "milestone_en": "After installation & handover", "milestone_th": "หลังติดตั้งเสร็จและส่งมอบงาน"},
        ],
    },
    "created_at": utcnow().isoformat(),
    "updated_at": utcnow().isoformat(),
    "created_by": "claude-agent",
}


def create_template(db_new):
    """Store quotation template schema in document-templates collection."""
    ref = db_new.collection("document-templates").document("areda-quotation")
    ref.set(QUOTATION_TEMPLATE)
    print(f"Created template: areda-quotation")


def create_counter_doc(db_new):
    """Create the document counter for quotation codes."""
    ref = db_new.collection("document_counters").document("quotation-2026")
    ref.set({
        "document_type": "quotation",
        "prefix": "AQ",
        "year": 2026,
        "last_number": 2,
        "updated_at": utcnow().isoformat(),
    })
    print("Created counter: quotation-2026 (last_number=2)")


def migrate_records(db_old, db_new):
    """Copy areda_quotations from (default) to document-records in go-documents."""
    src = db_old.collection("areda_quotations")
    dst_collection = "document-records"
    migrated = 0

    for doc in src.stream():
        data = doc.to_dict()
        data["document_type"] = "quotation"
        data["template_id"] = "areda-quotation"
        data["migrated_from"] = {
            "database": "(default)",
            "collection": "areda_quotations",
            "document_id": doc.id,
            "migrated_at": utcnow().isoformat(),
        }

        db_new.collection(dst_collection).document(doc.id).set(data)
        code = data.get("quotation_code", "?")
        lang = data.get("language", "?")
        print(f"  Migrated {code} ({lang}) -> document-records/{doc.id}")
        migrated += 1

    print(f"Total migrated: {migrated} documents")
    return migrated


def main():
    db_old = firestore.Client(project="ai-agents-go")
    db_new = firestore.Client(project="ai-agents-go", database="go-documents")

    print("=== Step 1: Create document-templates ===")
    create_template(db_new)

    print("\n=== Step 2: Create document counters ===")
    create_counter_doc(db_new)

    print("\n=== Step 3: Migrate areda_quotations -> document-records ===")
    migrate_records(db_old, db_new)

    print("\nDone! All data in go-documents database (asia-southeast1)")


if __name__ == "__main__":
    main()
