"""Firestore document models for Material Approval (Request for Material Approval).

Collection: document-records (shared)
Running code format: MA{YY}-{NNN} (year prefix + 3-digit running number)
Template ID: leka-material-approval
Source: imported from 2026 Leka Materal Approvals Codex
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ----------------------------------------------------------------------
# Enums
# ----------------------------------------------------------------------

class MaterialApprovalStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    FOR_INFORMATION = "for_information"
    FOR_APPROVAL = "for_approval"
    APPROVED = "approved"
    REVISED = "revised"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalDecision(str, Enum):
    FOR_APPROVAL = "for_approval"
    FOR_INFORMATION = "for_information"
    OTHERS = "others"
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


# ----------------------------------------------------------------------
# Sub-models
# ----------------------------------------------------------------------

class MaterialAttachment(BaseModel):
    """Supporting brochure, PDF, spec sheet, or Notion file."""

    name: str
    url: str = ""
    content_type: str = ""           # application/pdf, image/png, etc.


class MaterialImage(BaseModel):
    """Product or swatch photo for a material."""

    url: str
    caption: str = ""
    role: str = "gallery"            # gallery, primary, swatch, detail
    credit: str = ""                 # e.g., "Serge Ferrari"


class ColorSwatch(BaseModel):
    """Single color swatch within a material's color palette."""

    code: str                        # Manufacturer swatch code, e.g., "502-50202"
    name: str                        # Human-readable, e.g., "White"
    hex: str = ""                    # "#F5F2E8"
    finish: str = ""                 # "satin", "matte", etc.
    image_url: str = ""              # Optional swatch photo
    notes: str = ""                  # e.g., "verify against physical sample"


class ProjectInfo(BaseModel):
    """Project reference for the material approval request."""

    project_name: str = ""
    project_code: str = ""           # e.g., SO26-019, GO-RFA-114
    client_owner: str = ""
    consultant_designer: str = ""


class ApprovalParty(BaseModel):
    """A single party signing off on the material (consultant / designer / owner)."""

    role: str                        # "Consultant", "Designer", "Project Owner"
    name: str = ""
    company: str = ""
    decision: ApprovalDecision = ApprovalDecision.PENDING
    signed_at: datetime | None = None
    notes: str = ""


class MaterialRecord(BaseModel):
    """Single material entry (mirrors Codex `materials` collection fields).

    Schema source: 2026 Leka Materal Approvals Codex/src/materials/schema.js
    """

    material_name: str                           # Human-readable title
    code: str = ""                               # Internal or manufacturer code
    description: str = ""
    category: str = ""                           # Fabric, Flooring, Panel, etc.
    main_application: str = ""                   # Shade Structure, Kids Club wall, etc.
    attachments: list[MaterialAttachment] = Field(default_factory=list)
    images: list[MaterialImage] = Field(default_factory=list)
    colors: list[ColorSwatch] = Field(default_factory=list)
    manufacturer_product_url: str = ""

    # Optional enrichment fields pulled from datasheets (e.g., Soltis 502)
    composition: str = ""
    weight: str = ""                             # "590 g/m²"
    thickness: str = ""                          # "0.45 mm"
    roll_width: str = ""                         # "180 cm"
    use_cases: list[str] = Field(default_factory=list)


# ----------------------------------------------------------------------
# Main material approval document
# ----------------------------------------------------------------------

class MaterialApproval(BaseModel):
    """Root document in the document-records collection (go-documents DB).

    Database: go-documents (asia-southeast1)
    Collection: document-records
    Document ID: equals `approval_code` (e.g., MA26-001)
    Approval code: MA{YY}-{NNN}
    """

    # --- Document Type (for multi-type collection) ---
    document_type: str = "material-approval"
    template_id: str = "leka-material-approval"
    document_url: str = ""                       # https://docs.leka.studio/material-approvals/<doc_id>

    # --- Identity ---
    approval_code: str                           # MA26-001, MA26-002, ...
    document_ref: str = ""                       # e.g., MAT-SOLTIS-502-PROOF or GO-RFA-001
    revision_no: int = 0
    status: MaterialApprovalStatus = MaterialApprovalStatus.DRAFT
    language: str = "en"
    title: str = ""                              # "Soltis 502 Proof" or similar

    # --- Project ---
    project: ProjectInfo = Field(default_factory=ProjectInfo)

    # --- Materials (1..N per approval request) ---
    materials: list[MaterialRecord] = Field(default_factory=list)

    # --- Approval Routing ---
    approvals: list[ApprovalParty] = Field(default_factory=list)

    # --- Submission metadata ---
    prepared_by: str = "GO Corporation Co., Ltd."
    submission_notes: str = ""
    formal_note: str = ""

    # --- Dates ---
    issue_date: datetime = Field(default_factory=_utcnow)
    document_date: datetime = Field(default_factory=_utcnow)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    submitted_at: datetime | None = None
    approved_at: datetime | None = None

    # --- Audit ---
    created_by: str = ""
    updated_by: str = ""
    revision_history: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""

    def to_firestore(self) -> dict[str, Any]:
        """Serialize to Firestore-compatible dict."""
        return self.model_dump(mode="json")


# ----------------------------------------------------------------------
# Counter document (for running number generation)
# ----------------------------------------------------------------------

class MaterialApprovalCounter(BaseModel):
    """Stored in document_counters/material-approval-{year} to track running numbers.

    Document ID: "material-approval-2026", "material-approval-2027", etc.
    """

    document_type: str = "material-approval"
    prefix: str = "MA"
    year: int
    last_number: int = 0
    updated_at: datetime = Field(default_factory=_utcnow)
