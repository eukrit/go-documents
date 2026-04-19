"""Push Tensile Technic material-approval records for every Serge Ferrari PVC product.

Reads data/material-approvals.seed.json (the Leka Studio seed of 49 stubs) and:
  - Emits a parallel set of records under business_unit="Tensile Technic"
  - Uses template_id="tensile-technic-material-approval"
  - Remaps codes MA26-00N -> TT-26-00(N+1)  (TT-26-001 reserved for Soltis 502 Proof)
  - Prepends TT-26-001 Soltis 502 Proof with full enrichment (mirrors MA26-001
    created by push_material_approval_firestore.py)

Idempotent. Writes to document-records and advances the TT counter at
document_counters/material-approval-2026-tensile-technic.

Usage:
    python push_material_approvals_tensile_technic.py [--dry-run]
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import firestore

# --- Config ---
DATABASE = "go-documents"
RECORDS_COLLECTION = "document-records"
COUNTERS_COLLECTION = "document_counters"
SEED_PATH = Path(__file__).parent / "data" / "material-approvals.seed.json"
COUNTER_DOC_ID = "material-approval-2026-tensile-technic"
BUSINESS_UNIT = "Tensile Technic"
TEMPLATE_ID = "tensile-technic-material-approval"

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


def remap_code(ma_code: str) -> str:
    """Map MA26-NNN -> TT-26-NNN (same ordinal). TT-26-001 is reserved for
    Soltis 502 Proof (mirrors MA26-001); the Leka seed already skips 001, so
    this is a zero-shift remap.
    """
    m = re.match(r"^MA(\d{2})-(\d+)$", ma_code)
    if not m:
        raise ValueError(f"Unexpected code format: {ma_code}")
    yy, n = m.group(1), int(m.group(2))
    return f"TT-{yy}-{n:03d}"


def soltis_502_record() -> dict:
    """TT-26-001 — Soltis 502 Proof full-enrichment record.

    Mirrors the Leka MA26-001 written by push_material_approval_firestore.py
    but under Tensile Technic branding.
    """
    now = datetime.now(timezone.utc).isoformat()
    return {
        "document_type": "material-approval",
        "template_id": TEMPLATE_ID,
        "business_unit": BUSINESS_UNIT,
        "document_url": "https://docs.leka.studio/material-approvals/TT-26-001",

        "approval_code": "TT-26-001",
        "document_ref": "MAT-SOLTIS-502-PROOF",
        "revision_no": 0,
        "status": "submitted",
        "language": "en",
        "title": "Soltis 502 Proof",

        "project": {
            "project_name": "Material Library",
            "project_code": "",
            "client_owner": "Internal material library record for future submissions.",
            "consultant_designer": "To be assigned per project submission.",
        },

        "materials": [
            {
                "material_name": "Soltis 502 Proof",
                "code": "502V3",
                "description": (
                    "Colorful, durable, waterproof membrane made with 100% recycled polyester yarns. "
                    "The datasheet highlights a satin finish, strong UV durability, ease of upkeep, "
                    "glare control, and reliable long-term dimensional stability through Serge Ferrari's "
                    "Précontraint technology."
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
                "use_cases": ["Shade sails", "Fixed pergola roofs", "Retractable pergola roofs"],
            }
        ],

        "approvals": [
            {"role": "Consultant",          "decision": "pending"},
            {"role": "Structural Engineer", "decision": "pending"},
            {"role": "Project Owner",       "decision": "pending"},
        ],

        "prepared_by": "GO Corporation Co., Ltd.",
        "formal_note": (
            "Soltis 502 Proof is suitable as a waterproof fabric membrane for exterior solar "
            "protection. According to the brochure, its main applications include shade sails, "
            "fixed pergola roofs, and retractable pergola roofs. This material page can be "
            "reused as a starting point for future project-specific RFAs under Tensile Technic."
        ),
        "submission_notes": "",

        "issue_date": "2026-04-01T00:00:00Z",
        "document_date": "2026-04-01T00:00:00Z",
        "created_at": now,
        "updated_at": now,
        "submitted_at": now,

        "created_by": "eukrit@goco.bz",
        "updated_by": "eukrit@goco.bz",
        "notes": "TT-26-001 — Soltis 502 Proof material library entry under Tensile Technic.",

        "_seed": {"family": "Soltis", "source_url": "https://www.sergeferrari.com/en/products/soltis/502-proof/"},
    }


def build_stub_record(entry: dict, tt_code: str) -> dict:
    """Transform a Leka seed stub into a Tensile Technic record."""
    now = datetime.now(timezone.utc).isoformat()
    family = entry.get("family", "SF")

    material = {
        "material_name": entry["title"],
        "code": "",
        "description": entry.get("description", ""),
        "category": entry.get("category", ""),
        "main_application": entry.get("main_application", ""),
        "attachments": [],
        "images": [],
        "colors": [],
        "manufacturer_product_url": entry.get("url", ""),
        "composition": "",
        "weight": "",
        "thickness": "",
        "roll_width": "",
        "use_cases": [],
    }

    return {
        "document_type": "material-approval",
        "template_id": TEMPLATE_ID,
        "business_unit": BUSINESS_UNIT,
        "document_url": f"https://docs.leka.studio/material-approvals/{tt_code}",

        "approval_code": tt_code,
        "document_ref": f"MAT-{family.upper().replace(' ', '-').replace('/', '-')}-{tt_code}",
        "revision_no": 0,
        "status": "draft",
        "language": "en",
        "title": entry["title"],

        "project": {
            "project_name": "Material Library",
            "project_code": "",
            "client_owner": "Internal material library record for future submissions.",
            "consultant_designer": "To be assigned per project submission.",
        },

        "materials": [material],

        "approvals": [
            {"role": "Consultant",          "decision": "pending"},
            {"role": "Structural Engineer", "decision": "pending"},
            {"role": "Project Owner",       "decision": "pending"},
        ],

        "prepared_by": "GO Corporation Co., Ltd.",
        "formal_note": (
            f"{entry['title']} — {family} PVC-coated polyester from Serge Ferrari. "
            f"Tensile Technic material library stub. Enrich with images, color palette, and "
            f"datasheet facts per docs/material-approval-SOP.md before submitting for a project RFA."
        ),
        "submission_notes": "",

        "issue_date": now,
        "document_date": now,
        "created_at": now,
        "updated_at": now,
        "submitted_at": None,
        "approved_at": None,

        "created_by": "eukrit@goco.bz",
        "updated_by": "eukrit@goco.bz",
        "notes": "Seeded under Tensile Technic from data/material-approvals.seed.json (Serge Ferrari PVC catalog).",

        "_seed": {"family": family, "source_url": entry.get("url", "")},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not SEED_PATH.exists():
        print(f"[ERR] Seed file not found: {SEED_PATH}", file=sys.stderr)
        return 1

    with SEED_PATH.open("r", encoding="utf-8") as f:
        seed = json.load(f)
    entries = seed.get("entries", [])
    if not entries:
        print("[ERR] Seed has no entries.", file=sys.stderr)
        return 1

    records: list[dict] = []
    records.append(soltis_502_record())
    for entry in entries:
        tt_code = remap_code(entry["approval_code"])
        records.append(build_stub_record(entry, tt_code))

    codes = [r["approval_code"] for r in records]
    if len(set(codes)) != len(codes):
        dupes = {c for c in codes if codes.count(c) > 1}
        print(f"[ERR] Duplicate codes: {sorted(dupes)}", file=sys.stderr)
        return 1

    db = None
    if not args.dry_run:
        db = firestore.Client(database=DATABASE)
        print(f"Connected to Firestore database: {DATABASE}\n")
    else:
        print("[DRY] Dry run — no Firestore writes.\n")

    for rec in records:
        code = rec["approval_code"]
        if args.dry_run:
            print(f"[DRY] document-records/{code} — {rec['title']}")
        else:
            assert db is not None
            db.collection(RECORDS_COLLECTION).document(code).set(rec)
            print(f"[OK]  document-records/{code} — {rec['title']}")

    # Counter
    max_num = max(int(re.match(r"^TT-\d{2}-(\d+)$", c).group(1)) for c in codes)
    if args.dry_run:
        print(f"\n[DRY] document_counters/{COUNTER_DOC_ID} -> last_number>={max_num}")
    else:
        assert db is not None
        ref = db.collection(COUNTERS_COLLECTION).document(COUNTER_DOC_ID)
        snap = ref.get()
        current = snap.to_dict().get("last_number", 0) if snap.exists else 0
        new_last = max(current, max_num)
        ref.set({
            "document_type": "material-approval",
            "prefix": "TT",
            "year": 2026,
            "business_unit": BUSINESS_UNIT,
            "last_number": new_last,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        print(f"\n[OK]  document_counters/{COUNTER_DOC_ID} -> last_number={new_last} (was {current})")

    print(f"\n{'Would write' if args.dry_run else 'Wrote'} {len(records)} Tensile Technic material-approval records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
