"""Register Tensile Technic template records in document-templates.

Creates three templates under the Tensile Technic business unit:
  - tensile-technic-quotation           (EN + TH HTML pair)
  - tensile-technic-playground-inspection
  - tensile-technic-material-approval

Design tokens reference: Tensile Technic Design System (Figma HOwMIRipr2i6fH5ihbzhDz).
"""

import os
from datetime import datetime, timezone

from google.cloud import firestore

DATABASE = "go-documents"
TEMPLATES_COLLECTION = "document-templates"

CREDS_PATH = os.path.join(
    os.path.expanduser("~"),
    "OneDrive", "Documents", "Claude Code",
    "Credentials Claude Code",
    "ai-agents-go-4c81b70995db.json",
)
if os.path.exists(CREDS_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDS_PATH


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


TT_DESIGN_SYSTEM = {
    "font": "Inter",
    "font_mono": "JetBrains Mono",
    "colors": {
        "tt_navy": "#0F1B2E",
        "tt_bone": "#F3EEE5",
        "tt_accent_orange": "#D06B2A",
        "tt_surface": "#FAF7F0",
        "tt_ink": "#0F1B2E",
        "tt_muted": "#5C6B82",
        "tt_amber": "#F59E0B",
        "tt_copper": "#C94F15",
        "tt_tension_red": "#B23A0F",
    },
    "radius": {"xl": "22px", "lg": "16px", "md": "10px"},
    "page_size": "A4",
    "orientation": "portrait",
    "figma_source": "https://www.figma.com/design/HOwMIRipr2i6fH5ihbzhDz/Tensile-Technic-Design-System-Codex",
    "note": "Palette values are Tensile Technic reference tokens; sync with Figma when specific node IDs are supplied.",
}


TEMPLATES = [
    {
        "template_id": "tensile-technic-quotation",
        "document_type": "quotation",
        "business_unit": "Tensile Technic",
        "brand": "Tensile Technic",
        "title": "Tensile Technic — Quotation",
        "code_format": "TQ-{YY}{NNN}",
        "code_prefix": "TQ",
        "template_file": "quotation-template-tensile-technic.html",
        "template_file_th": "quotation-template-tensile-technic-th.html",
        "design_system": TT_DESIGN_SYSTEM,
        "language_variants": ["en", "th"],
    },
    {
        "template_id": "tensile-technic-playground-inspection",
        "document_type": "playground_inspection",
        "business_unit": "Tensile Technic",
        "brand": "Tensile Technic",
        "title": "Tensile Technic — Playground Safety Inspection Certificate",
        "revision": "R1",
        "code_format": "TS-{YY}-{NNN}",
        "code_prefix": "TS",
        "template_file": "playground-inspection-template-tensile-technic.html",
        "design_system": TT_DESIGN_SYSTEM,
    },
    {
        "template_id": "tensile-technic-material-approval",
        "document_type": "material-approval",
        "business_unit": "Tensile Technic",
        "brand": "Tensile Technic",
        "title": "Tensile Technic — Request for Material Approval",
        "code_format": "TT-{YY}-{NNN}",
        "code_prefix": "TT",
        "template_file": "material-approval-template-tensile-technic.html",
        "example_file": "docs/materials/soltis-502-proof.html",
        "design_system": TT_DESIGN_SYSTEM,
        "approval_roles_default": ["Consultant", "Structural Engineer", "Project Owner"],
    },
]


def main() -> int:
    db = firestore.Client(database=DATABASE)
    print(f"Connected to Firestore database: {DATABASE}\n")

    created_at = now()
    for tpl in TEMPLATES:
        payload = {**tpl, "created_at": created_at, "updated_at": created_at}
        ref = db.collection(TEMPLATES_COLLECTION).document(tpl["template_id"])
        ref.set(payload)
        print(f"[OK] document-templates/{tpl['template_id']}")

    print(f"\nRegistered {len(TEMPLATES)} Tensile Technic templates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
