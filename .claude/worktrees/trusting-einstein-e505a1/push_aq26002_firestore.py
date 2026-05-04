"""Push AQ-26002 EN + TH quotations to Firestore areda_quotations collection."""

import os
import sys
from datetime import datetime, timedelta, timezone

# Point to GCP service account
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    r"C:\Users\eukri\OneDrive\Documents\Claude Code"
    r"\Credentials Claude Code\ai-agents-go-4c81b70995db.json"
)
os.environ["GOOGLE_CLOUD_PROJECT"] = "ai-agents-go"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from google.cloud import firestore

COLLECTION = "areda_quotations"
COUNTER_COLLECTION = "areda_quotation_counters"


def utcnow():
    return datetime.now(timezone.utc)


def build_quotation(language: str) -> dict:
    """Build AQ-26002 document for the given language."""
    now = utcnow()
    valid_until = now + timedelta(days=15)
    is_th = language == "th"

    items = [
        {
            "item_no": 1,
            "product_code": "AA-HW-FD01",
            "description": (
                "ชุดอุปกรณ์ประตูพับไม้หลายบาน OPK"
                if is_th
                else "OPK Multi-Panel Folding Wooden Door Hardware System"
            ),
            "description_sub": (
                "ชุดอุปกรณ์สำหรับประตูพับไม้ 2–6 บาน (≥40 กก./บาน) "
                "รวม: ชุดอุปกรณ์ประตูพับ ×1, ลูกล้อแขวนเลื่อน ×2, "
                "บานพับซ่อนสปริง ×9 (3/ช่อง), รางประตูพับ 6,000 มม. อโนไดซ์แชมเปญ "
                "รวมค่าขนส่งทางเรือ ประกันภัย ศุลกากร อากรขาเข้า"
                if is_th
                else "Complete hardware kit for 2–6 panel folding wooden doors (≥40 kg/panel). "
                "Includes: multi folding door hardware ×1, hanging sliding rollers ×2, "
                "hidden elastic hinges ×9 (3/door slot), folding door track 6,000 mm anodised champagne. "
                "Includes sea freight, cargo insurance, customs clearance, import duty."
            ),
            "unit": "ชุด" if is_th else "set",
            "qty": 1.0,
            "unit_rate": 19500.00,
            "amount": 19500.00,
            "category": "อุปกรณ์ประตู — นำเข้า" if is_th else "Door Hardware — Imported",
            "vendor": "OPK Smart Home (Guangdong OPK Smart Home Technology Co., Ltd.)",
            "notes": (
                "OPK PI 20260331: CA340003-003 $16, CA990275-002 $5.60×2, "
                "CA992513-001 $5.30×9, A1259-X002 $18.90. FOB Guangzhou USD 93.80"
            ),
        },
        {
            "item_no": 2,
            "product_code": "—",
            "description": (
                "ค่าขนส่งระหว่างประเทศ พิธีการศุลกากร และจัดส่งถึงหน้างาน"
                if is_th
                else "International Freight, Customs Clearance & Local Delivery to Site"
            ),
            "description_sub": (
                "ขนส่งทางเรือ LCL จงซาน→กรุงเทพฯ, ประกันภัย Chubb, ศุลกากร HS 8302 @10%, "
                "ค่าบริการผ่านพิธีการ, ขนส่งปลายทาง — รวมอยู่ในรายการที่ 1 แล้ว"
                if is_th
                else "Sea LCL Zhongshan→Bangkok, Chubb cargo insurance, Thai customs HS 8302 @10%, "
                "clearance service fee, last-mile delivery — included in item 1"
            ),
            "unit": "ล็อต" if is_th else "lot",
            "qty": 1.0,
            "unit_rate": 0.0,
            "amount": 0.0,
            "category": "โลจิสติกส์" if is_th else "Logistics",
            "vendor": "",
            "notes": "Included in item 1 pricing",
        },
    ]

    categories = (
        ["อุปกรณ์ประตู — นำเข้า", "โลจิสติกส์"]
        if is_th
        else ["Door Hardware — Imported", "Logistics"]
    )

    subtotal = 19500.00
    vat_amount = 1365.00
    grand_total = 20865.00

    schedule = [
        {
            "name": "วางมัดจำและยืนยันคำสั่งซื้อ" if is_th else "Deposit & Order Confirmation",
            "duration_text": "",
            "target_date": None,
            "actual_date": None,
            "notes": "",
        },
        {
            "name": "ผลิต" if is_th else "Production",
            "duration_text": "30–35 วันทำการ" if is_th else "30–35 working days",
            "target_date": None,
            "actual_date": None,
            "notes": "",
        },
        {
            "name": "ขนส่งและผ่านพิธีการศุลกากร" if is_th else "Shipping & Customs Clearance",
            "duration_text": "14–21 วัน" if is_th else "14–21 days",
            "target_date": None,
            "actual_date": None,
            "notes": "",
        },
        {
            "name": "จัดส่งถึงหน้างาน" if is_th else "Delivery to Site",
            "duration_text": "1–3 วัน" if is_th else "1–3 days",
            "target_date": None,
            "actual_date": None,
            "notes": "",
        },
    ]

    payment_terms = [
        {
            "payment_no": 1,
            "percentage": 50.0,
            "milestone": (
                "มัดจำเมื่อลงนามสัญญา / ยืนยันคำสั่งซื้อ"
                if is_th
                else "Deposit upon signing contract / order confirmation"
            ),
            "amount": 10432.50,
            "status": "pending",
            "due_date": None,
            "paid_date": None,
            "invoice_no": "",
        },
        {
            "payment_no": 2,
            "percentage": 40.0,
            "milestone": (
                "ก่อนสินค้าออกจากโรงงานต้นทาง / ก่อนจัดส่งระหว่างประเทศ"
                if is_th
                else "Before goods depart origin factory / prior to international shipment"
            ),
            "amount": 8346.00,
            "status": "pending",
            "due_date": None,
            "paid_date": None,
            "invoice_no": "",
        },
        {
            "payment_no": 3,
            "percentage": 10.0,
            "milestone": (
                "เมื่อส่งมอบถึงหน้างานและยืนยันรับสินค้า"
                if is_th
                else "Upon delivery to site and goods receipt confirmation"
            ),
            "amount": 2086.50,
            "status": "pending",
            "due_date": None,
            "paid_date": None,
            "invoice_no": "",
        },
    ]

    return {
        "quotation_code": "AQ-26002",
        "revision_no": 0,
        "status": "draft",
        "language": language,
        "customer": {
            "attn": "",
            "company": "",
            "address": "",
            "tax_id": "",
            "email": "",
            "tel": "",
        },
        "project_name": "",
        "subject": (
            "ชุดอุปกรณ์ประตูพับไม้หลายบาน — OPK Series"
            if is_th
            else "Multi-Panel Folding Wooden Door Hardware System — OPK Series"
        ),
        "proposed_by": {"name": "", "email": "", "mobile": ""},
        "items": items,
        "categories": categories,
        "currency": "THB",
        "fx_rate": 33.52,
        "fx_base_currency": "USD",
        "subtotal": subtotal,
        "vat_rate": 7.0,
        "vat_amount": vat_amount,
        "grand_total": grand_total,
        "discount_amount": 0.0,
        "discount_note": "",
        "schedule": schedule,
        "payment_terms": payment_terms,
        "attachments": [],
        "generated_pdf": None,
        "valid_days": 15,
        "valid_until": valid_until.isoformat(),
        "document_date": now.isoformat(),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "sent_at": None,
        "accepted_at": None,
        "expired_at": None,
        "created_by": "claude-agent",
        "updated_by": "claude-agent",
        "revision_history": [],
        "notes": (
            "Source: OPK PI 20260331 (Guangdong OPK Smart Home Technology Co., Ltd). "
            "FOB Guangzhou USD 93.80. FX rate 33.52 THB/USD (BOT 32.54 + 3% buffer). "
            "Landed cost ~THB 14,255. Selling at THB 19,500 (~27% GM)."
        ),
    }


def main():
    db = firestore.Client(project="ai-agents-go")

    # Update counter to 2
    counter_ref = db.collection(COUNTER_COLLECTION).document("2026")
    counter_snap = counter_ref.get()
    current_last = counter_snap.get("last_number") if counter_snap.exists else 0
    if current_last < 2:
        counter_ref.set(
            {"year": 2026, "last_number": 2, "updated_at": utcnow().isoformat()}
        )
        print(f"Counter updated: {current_last} -> 2")
    else:
        print(f"Counter already at {current_last}, no update needed")

    for lang in ("en", "th"):
        doc_data = build_quotation(lang)
        # Check if document already exists
        existing = (
            db.collection(COLLECTION)
            .where("quotation_code", "==", "AQ-26002")
            .where("language", "==", lang)
            .limit(1)
            .stream()
        )
        existing_doc = next(existing, None)
        if existing_doc:
            existing_doc.reference.update(doc_data)
            print(f"Updated existing {lang.upper()} document: {existing_doc.id}")
        else:
            doc_ref = db.collection(COLLECTION).document()
            doc_ref.set(doc_data)
            print(f"Created {lang.upper()} document: {doc_ref.id}")

    print("\nDone! AQ-26002 EN + TH pushed to Firestore.")


if __name__ == "__main__":
    main()
