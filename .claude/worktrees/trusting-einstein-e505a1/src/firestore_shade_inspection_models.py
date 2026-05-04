"""Firestore document models for Tensile / Shade Structure Safety Inspection Certificates.

Collection: document-records (shared)
Running code format: TSI-{YY}-{NNN}  (Tensile Shade Inspection)
Template ID: tensile-technic-shade-inspection
Business unit: Tensile Technic

Standards referenced on the report:
- ASCE/SEI 55 "Tensile Membrane Structures" (fabric-tension structures design standard)
- NFPA 701 "Fire Tests for Flame Propagation of Textiles and Films"
- ASTM D751, D5034, D4851 (coated-fabric mechanical tests)
- EN 13782 "Temporary structures — tents — safety" (Europe)
- AS 2428 "Shade fabrics for commercial and domestic use" (Australia)
- AS/NZS 1170 "Structural design actions" (wind/weight/seismic loading)
- IFAI / Tensile Membrane Association — Tensile Structures Maintenance Guide
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

class ShadeInspectionStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    REVISED = "revised"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class InspectionScope(str, Enum):
    ROUTINE_VISUAL = "routine_visual"              # monthly / quarterly by owner
    COMPREHENSIVE_ANNUAL = "comprehensive_annual"  # yearly, qualified inspector
    POST_EVENT = "post_event"                      # after storm / wind > threshold
    ENGINEERING_REVIEW = "engineering_review"      # 5-year full structural review


class ComplianceResult(str, Enum):
    PASS = "pass"
    PASS_WITH_RECOMMENDATIONS = "pass_with_recommendations"   # minor maintenance < 30d
    CONDITIONAL_CORRECTIVE_ACTION = "conditional_corrective_action"
    FAIL = "fail"                                             # immediate action required


class Severity(str, Enum):
    OK = "ok"
    ADVISORY = "advisory"                   # note for future inspection
    MONITOR = "monitor"                     # track at next inspection
    ACTION_30_DAYS = "action_30_days"
    ACTION_IMMEDIATE = "action_immediate"   # remove from service / secure


class StructureType(str, Enum):
    SHADE_SAIL = "shade_sail"                      # tensioned triangular/quad sail
    TENSIONED_MEMBRANE = "tensioned_membrane"      # conic, hypar, barrel
    PERGOLA_RETRACTABLE = "pergola_retractable"
    PERGOLA_FIXED = "pergola_fixed"
    CANOPY_CANTILEVERED = "canopy_cantilevered"
    UMBRELLA_LARGE = "umbrella_large"
    ETFE_CUSHION = "etfe_cushion"
    OTHER = "other"


# ----------------------------------------------------------------------
# Sub-models
# ----------------------------------------------------------------------

class SiteInfo(BaseModel):
    """Shade structure site & installation details."""

    structure_name: str = ""
    site_location: str = ""
    site_location_short: str = ""
    owner_operator: str = ""
    installation_date: datetime | None = None
    structure_type: StructureType = StructureType.SHADE_SAIL
    fabric_product: str = ""              # e.g., "Serge Ferrari Soltis 502 Proof"
    fabric_color_code: str = ""           # e.g., "502V3-8450C (Black)"
    approximate_area_sqm: float = 0.0
    anchor_point_count: int = 0
    design_wind_speed_kmh: float = 0.0    # per AS/NZS 1170 or equivalent


class ClientInfo(BaseModel):
    attn: str = ""
    company: str = ""
    email: str = ""
    tel: str = ""


class InspectorInfo(BaseModel):
    """Inspector credentials.

    For commercial tensile structures, the inspector is typically a
    licensed Professional Engineer or an IFAI / Tensile Membrane Association
    certified inspector.
    """

    name: str = ""
    company: str = "GO Corporation Co., Ltd. / Tensile Technic"
    credential: str = ""                  # e.g., "IFAI Certified / MEng Structural"
    license_no: str = ""
    license_expiration: str = ""


class FindingItem(BaseModel):
    """A single finding within a checklist system."""

    item: str                             # e.g., "Fabric seam integrity"
    severity: Severity = Severity.OK
    observation: str = ""                 # free-text finding
    photo_refs: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    due_date: datetime | None = None
    standard_ref: str = ""                # e.g., "ASCE/SEI 55 §7.3", "AS 2428-1998"


class SystemFindings(BaseModel):
    """Grouped findings for one inspection system."""

    system: str                           # "Membrane", "Hardware", "Structural", etc.
    findings: list[FindingItem] = Field(default_factory=list)


class WarrantyBlock(BaseModel):
    handover_date: datetime | None = None
    warranty_months: int = 60             # typical tensile structure warranty
    warranty_start: str = ""
    warranty_end: str = ""
    warranty_scope: str = "Fabric and structural — as per supply agreement."


# ----------------------------------------------------------------------
# Main shade inspection document
# ----------------------------------------------------------------------

class ShadeInspectionCertificate(BaseModel):
    """Root document in the document-records collection (go-documents DB).

    Collection: document-records
    Document ID: equals `report_no` (e.g., TSI-26-001)
    Report code: TSI-{YY}-{NNN}
    """

    # --- Document Type ---
    document_type: str = "shade-inspection"
    template_id: str = "tensile-technic-shade-inspection"
    business_unit: str = "Tensile Technic"
    document_url: str = ""

    # --- Identity ---
    report_no: str                        # TSI-26-001, TSI-26-002, ...
    revision_no: int = 1
    revision_label: str = "R1"
    status: ShadeInspectionStatus = ShadeInspectionStatus.DRAFT
    language: str = "en"

    # --- Site + Structure ---
    site: SiteInfo = Field(default_factory=SiteInfo)
    client: ClientInfo = Field(default_factory=ClientInfo)

    # --- Inspection ---
    inspection_date: datetime | None = None
    inspection_scope: InspectionScope = InspectionScope.COMPREHENSIVE_ANNUAL
    inspection_duration_hours: float = 0.0
    reinspection_recommended: str = ""    # e.g., "March 2027"
    compliance_result: ComplianceResult = ComplianceResult.PASS

    # --- Findings (checklist by system) ---
    findings: list[SystemFindings] = Field(
        default_factory=lambda: [
            SystemFindings(system="Membrane / Fabric", findings=[]),
            SystemFindings(system="Seams, Edges & Perimeter", findings=[]),
            SystemFindings(system="Tension Hardware & Cables", findings=[]),
            SystemFindings(system="Structural Frame & Anchorage", findings=[]),
            SystemFindings(system="Drainage & Water Management", findings=[]),
            SystemFindings(system="Environmental & Site Context", findings=[]),
        ]
    )

    # --- Standards referenced on the report ---
    standards_applied: list[str] = Field(
        default_factory=lambda: [
            "ASCE/SEI 55 — Tensile Membrane Structures",
            "NFPA 701 — Fire Tests for Flame Propagation of Textiles and Films",
            "AS/NZS 1170 — Structural design actions (wind/load/seismic)",
            "AS 2428 — Shade fabrics for commercial and domestic use",
            "IFAI / TMA — Tensile Structures Maintenance Guide",
        ]
    )

    # --- Warranty ---
    warranty: WarrantyBlock = Field(default_factory=WarrantyBlock)

    # --- Inspector ---
    inspector: InspectorInfo = Field(default_factory=InspectorInfo)

    # --- Dates ---
    document_date: datetime = Field(default_factory=_utcnow)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    issued_at: datetime | None = None

    # --- Audit ---
    created_by: str = ""
    updated_by: str = ""
    revision_history: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""

    def to_firestore(self) -> dict[str, Any]:
        """Serialize to Firestore-compatible dict."""
        return self.model_dump(mode="json")
