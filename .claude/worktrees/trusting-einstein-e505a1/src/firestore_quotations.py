"""Firestore operations for GO Documents.

Handles CRUD, running number generation, URL generation, and PDF
attachment management for the document-records collection.

Live URL: https://docs.leka.studio/<document_type>/<doc_id>
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from google.cloud import firestore

from firestore_models import (
    AredaQuotation,
    AttachmentMeta,
    CustomerInfo,
    LineItem,
    PaymentTerm,
    ProposerInfo,
    QuotationCounter,
    QuotationStatus,
    ScheduleMilestone,
    make_document_url,
)

DATABASE = "go-documents"
COLLECTION = "document-records"
COUNTER_COLLECTION = "document_counters"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_db() -> firestore.Client:
    """Singleton Firestore client — go-documents database."""
    if not hasattr(get_db, "_client"):
        get_db._client = firestore.Client(database=DATABASE)
    return get_db._client


# ----------------------------------------------------------------------
# Running number: AQ-{YY}{NNN}
# ----------------------------------------------------------------------

def generate_quotation_code(year: int | None = None) -> str:
    """Generate the next quotation code using a Firestore transaction.

    Format: AQ-26001, AQ-26002, ...
    Uses a counter document in document_counters/quotation-{year}.
    """
    db = get_db()
    if year is None:
        year = _utcnow().year
    yy = str(year)[-2:]
    counter_ref = db.collection(COUNTER_COLLECTION).document(f"quotation-{year}")

    @firestore.transactional
    def _increment(transaction):
        snapshot = counter_ref.get(transaction=transaction)
        if snapshot.exists:
            last = snapshot.get("last_number")
        else:
            last = 0
        new_number = last + 1
        transaction.set(counter_ref, {
            "document_type": "quotation",
            "prefix": "AQ",
            "year": year,
            "last_number": new_number,
            "updated_at": _utcnow().isoformat(),
        })
        return new_number

    transaction = db.transaction()
    number = _increment(transaction)
    return f"AQ-{yy}{number:03d}"


# ----------------------------------------------------------------------
# CRUD
# ----------------------------------------------------------------------

def create_quotation(
    customer: CustomerInfo,
    project_name: str,
    subject: str,
    proposed_by: ProposerInfo,
    items: list[LineItem],
    categories: list[str] | None = None,
    payment_terms: list[PaymentTerm] | None = None,
    schedule: list[ScheduleMilestone] | None = None,
    language: str = "en",
    valid_days: int = 15,
    created_by: str = "",
    notes: str = "",
) -> tuple[str, AredaQuotation]:
    """Create a new quotation and return (doc_id, quotation)."""
    db = get_db()
    code = generate_quotation_code()

    # Calculate totals
    subtotal = sum(item.amount for item in items)
    vat_amount = round(subtotal * 7 / 100, 2)
    grand_total = round(subtotal + vat_amount, 2)

    # Default payment terms (30/30/30/10)
    if payment_terms is None:
        splits = [
            (1, 30.0, "มัดจำเมื่อลงนามสัญญา" if language == "th" else "Deposit upon signing contract"),
            (2, 30.0, "ก่อนจัดส่งจากต้นทาง" if language == "th" else "Before shipment from origin"),
            (3, 30.0, "เมื่อส่งมอบถึงหน้างาน" if language == "th" else "Upon delivery to site"),
            (4, 10.0, "หลังติดตั้งเสร็จและส่งมอบงาน" if language == "th" else "After installation & handover"),
        ]
        payment_terms = [
            PaymentTerm(
                payment_no=no,
                percentage=pct,
                milestone=desc,
                amount=round(grand_total * pct / 100, 2),
            )
            for no, pct, desc in splits
        ]

    # Default schedule
    if schedule is None:
        if language == "th":
            schedule = [
                ScheduleMilestone(name="รับเงินมัดจำ"),
                ScheduleMilestone(name="อนุมัติแบบ", duration_text="7–14 วัน"),
                ScheduleMilestone(name="จัดซื้อ / ผลิต", duration_text="45–90 วัน"),
                ScheduleMilestone(name="การขนส่งและศุลกากร", duration_text="30–45 วัน"),
                ScheduleMilestone(name="จัดส่งและติดตั้ง", duration_text="7–14 วันทำการ"),
            ]
        else:
            schedule = [
                ScheduleMilestone(name="Deposit Received"),
                ScheduleMilestone(name="Design Approval", duration_text="7–14 days"),
                ScheduleMilestone(name="Procurement / Production", duration_text="45–90 days"),
                ScheduleMilestone(name="Shipping & Customs", duration_text="30–45 days"),
                ScheduleMilestone(name="Delivery & Installation", duration_text="7–14 working days"),
            ]

    now = _utcnow()
    quotation = AredaQuotation(
        quotation_code=code,
        language=language,
        customer=customer,
        project_name=project_name,
        subject=subject,
        proposed_by=proposed_by,
        items=items,
        categories=categories or [],
        subtotal=subtotal,
        vat_amount=vat_amount,
        grand_total=grand_total,
        schedule=schedule,
        payment_terms=payment_terms,
        valid_days=valid_days,
        valid_until=now + timedelta(days=valid_days),
        document_date=now,
        created_at=now,
        updated_at=now,
        created_by=created_by,
        updated_by=created_by,
        notes=notes,
    )

    doc_ref = db.collection(COLLECTION).document()
    doc_ref.set(quotation.to_firestore())

    # Generate and store document URL (brand-aware)
    url = make_document_url("quotation", doc_ref.id, quotation.template_id)
    doc_ref.update({"document_url": url})
    quotation.document_url = url

    return doc_ref.id, quotation


def get_quotation(doc_id: str) -> AredaQuotation | None:
    """Fetch a quotation by Firestore document ID."""
    db = get_db()
    doc = db.collection(COLLECTION).document(doc_id).get()
    if not doc.exists:
        return None
    return AredaQuotation(**doc.to_dict())


def get_quotation_by_code(code: str) -> tuple[str, AredaQuotation] | None:
    """Fetch a quotation by its AQ-YYXXX code."""
    db = get_db()
    docs = (
        db.collection(COLLECTION)
        .where("quotation_code", "==", code)
        .limit(1)
        .stream()
    )
    for doc in docs:
        return doc.id, AredaQuotation(**doc.to_dict())
    return None


def update_quotation(doc_id: str, updates: dict, updated_by: str = "") -> None:
    """Partial update of a quotation document."""
    db = get_db()
    updates["updated_at"] = _utcnow().isoformat()
    if updated_by:
        updates["updated_by"] = updated_by
    db.collection(COLLECTION).document(doc_id).update(updates)


def update_status(doc_id: str, status: QuotationStatus, updated_by: str = "") -> None:
    """Update quotation status with timestamp tracking."""
    updates = {"status": status.value, "updated_by": updated_by}
    now = _utcnow().isoformat()
    if status == QuotationStatus.SENT:
        updates["sent_at"] = now
    elif status == QuotationStatus.ACCEPTED:
        updates["accepted_at"] = now
    elif status == QuotationStatus.EXPIRED:
        updates["expired_at"] = now
    update_quotation(doc_id, updates, updated_by)


def attach_generated_pdf(doc_id: str, pdf_meta: AttachmentMeta) -> None:
    """Attach the generated PDF to a quotation."""
    update_quotation(doc_id, {
        "generated_pdf": pdf_meta.model_dump(mode="json"),
    })


def list_quotations(
    status: QuotationStatus | None = None,
    limit: int = 50,
) -> list[tuple[str, AredaQuotation]]:
    """List quotations, optionally filtered by status."""
    db = get_db()
    query = db.collection(COLLECTION).order_by(
        "created_at", direction=firestore.Query.DESCENDING
    )
    if status:
        query = query.where("status", "==", status.value)
    query = query.limit(limit)

    results = []
    for doc in query.stream():
        results.append((doc.id, AredaQuotation(**doc.to_dict())))
    return results


def search_quotations(
    customer_company: str = "",
    project_name: str = "",
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = 50,
) -> list[tuple[str, AredaQuotation]]:
    """Search quotations by customer, project, or date range."""
    db = get_db()
    query = db.collection(COLLECTION)

    if customer_company:
        query = query.where("customer.company", "==", customer_company)
    if project_name:
        query = query.where("project_name", "==", project_name)
    if from_date:
        query = query.where("document_date", ">=", from_date.isoformat())
    if to_date:
        query = query.where("document_date", "<=", to_date.isoformat())

    query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
    query = query.limit(limit)

    results = []
    for doc in query.stream():
        results.append((doc.id, AredaQuotation(**doc.to_dict())))
    return results
