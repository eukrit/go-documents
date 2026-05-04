"""Firestore operations for Playground Safety Inspection Certificates.

Handles CRUD and running number generation for playground inspection
certificates in the document-records collection.
"""

from __future__ import annotations

from datetime import datetime, timezone

from google.cloud import firestore

from firestore_inspection_models import (
    ClientInfo,
    ComplianceResult,
    InspectionStatus,
    InspectorInfo,
    PlaygroundInspectionCertificate,
    SiteInfo,
    WarrantyPeriod,
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
# Running number: SO{YY}-{NNN}
# ----------------------------------------------------------------------

def generate_inspection_code(year: int | None = None) -> str:
    """Generate the next inspection code using a Firestore transaction.

    Format: SO25-001, SO25-002, ...
    Uses a counter document in document_counters/inspection-{year}.
    """
    db = get_db()
    if year is None:
        year = _utcnow().year
    yy = str(year)[-2:]
    counter_ref = db.collection(COUNTER_COLLECTION).document(f"inspection-{year}")

    @firestore.transactional
    def _increment(transaction):
        snapshot = counter_ref.get(transaction=transaction)
        if snapshot.exists:
            last = snapshot.get("last_number")
        else:
            last = 0
        new_number = last + 1
        transaction.set(counter_ref, {
            "document_type": "playground_inspection",
            "prefix": "SO",
            "year": year,
            "last_number": new_number,
            "updated_at": _utcnow().isoformat(),
        })
        return new_number

    transaction = db.transaction()
    number = _increment(transaction)
    return f"SO{yy}-{number:03d}"


# ----------------------------------------------------------------------
# CRUD
# ----------------------------------------------------------------------

def create_inspection(
    report_no: str,
    site: SiteInfo,
    client: ClientInfo,
    inspection_date: datetime,
    warranty: WarrantyPeriod,
    compliance_result: ComplianceResult = ComplianceResult.SUBSTANTIAL_COMPLIANCE,
    inspection_type: str = "Comprehensive Safety Inspection",
    reinspection_date: str = "",
    inspector: InspectorInfo | None = None,
    revision_no: int = 1,
    revision_label: str = "R1",
    created_by: str = "",
    notes: str = "",
) -> tuple[str, PlaygroundInspectionCertificate]:
    """Create a new inspection certificate and return (doc_id, certificate)."""
    db = get_db()

    if inspector is None:
        inspector = InspectorInfo()

    now = _utcnow()
    cert = PlaygroundInspectionCertificate(
        report_no=report_no,
        revision_no=revision_no,
        revision_label=revision_label,
        site=site,
        client=client,
        inspection_date=inspection_date,
        inspection_type=inspection_type,
        reinspection_date=reinspection_date,
        compliance_result=compliance_result,
        warranty=warranty,
        inspector=inspector,
        document_date=now,
        created_at=now,
        updated_at=now,
        created_by=created_by,
        updated_by=created_by,
        notes=notes,
    )

    doc_ref = db.collection(COLLECTION).document()
    doc_ref.set(cert.to_firestore())
    return doc_ref.id, cert


def get_inspection(doc_id: str) -> PlaygroundInspectionCertificate | None:
    """Fetch an inspection certificate by Firestore document ID."""
    db = get_db()
    doc = db.collection(COLLECTION).document(doc_id).get()
    if not doc.exists:
        return None
    return PlaygroundInspectionCertificate(**doc.to_dict())


def get_inspection_by_code(code: str) -> tuple[str, PlaygroundInspectionCertificate] | None:
    """Fetch an inspection certificate by its SO-YYXXX code."""
    db = get_db()
    docs = (
        db.collection(COLLECTION)
        .where("document_type", "==", "playground_inspection")
        .where("report_no", "==", code)
        .limit(1)
        .stream()
    )
    for doc in docs:
        return doc.id, PlaygroundInspectionCertificate(**doc.to_dict())
    return None


def update_inspection(doc_id: str, updates: dict, updated_by: str = "") -> None:
    """Partial update of an inspection certificate document."""
    db = get_db()
    updates["updated_at"] = _utcnow().isoformat()
    if updated_by:
        updates["updated_by"] = updated_by
    db.collection(COLLECTION).document(doc_id).update(updates)


def update_status(doc_id: str, status: InspectionStatus, updated_by: str = "") -> None:
    """Update inspection status with timestamp tracking."""
    updates = {"status": status.value, "updated_by": updated_by}
    now = _utcnow().isoformat()
    if status == InspectionStatus.ISSUED:
        updates["issued_at"] = now
    update_inspection(doc_id, updates, updated_by)


def list_inspections(
    status: InspectionStatus | None = None,
    limit: int = 50,
) -> list[tuple[str, PlaygroundInspectionCertificate]]:
    """List inspection certificates, optionally filtered by status."""
    db = get_db()
    query = (
        db.collection(COLLECTION)
        .where("document_type", "==", "playground_inspection")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
    )
    if status:
        query = query.where("status", "==", status.value)
    query = query.limit(limit)

    results = []
    for doc in query.stream():
        results.append((doc.id, PlaygroundInspectionCertificate(**doc.to_dict())))
    return results
