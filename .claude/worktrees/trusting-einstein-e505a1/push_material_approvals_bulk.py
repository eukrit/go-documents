"""Bulk push material-approval records from data/material-approvals.seed.json.

Database: go-documents (asia-southeast1)
Collections: document-templates, document-records, document_counters

Source of truth: data/material-approvals.seed.json (one entry per material).
Each entry is written to document-records/<approval_code> via .set() (idempotent).
The material-approval-{year} counter is advanced to the max last_number observed.

Usage:
    python push_material_approvals_bulk.py [--dry-run]

See docs/material-approval-SOP.md for the end-to-end workflow.
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
TEMPLATES_COLLECTION = "document-templates"
RECORDS_COLLECTION = "document-records"
COUNTERS_COLLECTION = "document_counters"
SEED_PATH = Path(__file__).parent / "data" / "material-approvals.seed.json"

# Credentials
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


def parse_code(code: str) -> tuple[int, int]:
    """Return (year_yy, number) parsed from a MA{YY}-{NNN} code."""
    m = re.match(r"^MA(\d{2})-(\d{3,})$", code)
    if not m:
        raise ValueError(f"Invalid approval_code: {code!r} (expected MA{{YY}}-{{NNN}})")
    return int(m.group(1)), int(m.group(2))


def build_record(entry: dict) -> dict:
    """Turn a seed entry into a full document-records payload."""
    code = entry["approval_code"]
    now = datetime.now(timezone.utc).isoformat()

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
        "template_id": "leka-material-approval",
        "document_url": f"https://docs.leka.studio/material-approvals/{code}",

        "approval_code": code,
        "document_ref": f"MAT-{entry.get('family', 'SF').upper().replace(' ', '-')}-{code}",
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
            {"role": "Consultant",    "decision": "pending"},
            {"role": "Designer",      "decision": "pending"},
            {"role": "Project Owner", "decision": "pending"},
        ],

        "prepared_by": "GO Corporation Co., Ltd.",
        "formal_note": (
            f"{entry['title']} — {entry.get('family', '')} PVC-coated polyester from Serge Ferrari. "
            f"Reusable material library stub. Enrich with images, color palette, and datasheet facts per "
            f"docs/material-approval-SOP.md before submitting for project approval."
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
        "notes": "Seeded from data/material-approvals.seed.json — Serge Ferrari PVC catalog batch.",

        "_seed": {
            "family": entry.get("family", ""),
            "source_url": entry.get("url", ""),
        },
    }


def ensure_template(db: firestore.Client) -> None:
    """Create the leka-material-approval template doc if missing."""
    ref = db.collection(TEMPLATES_COLLECTION).document("leka-material-approval")
    if ref.get().exists:
        print("[--] Template already present: document-templates/leka-material-approval")
        return
    ref.set({
        "template_id": "leka-material-approval",
        "document_type": "material-approval",
        "brand": "Leka Studio",
        "title": "Request for Material Approval",
        "code_format": "MA{YY}-{NNN}",
        "code_prefix": "MA",
        "template_file": "material-approval-template.html",
        "example_file": "docs/materials/soltis-502-proof.html",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    print("[OK] Template created: document-templates/leka-material-approval")


def push_entries(db: firestore.Client | None, entries: list[dict], dry_run: bool) -> dict[int, int]:
    """Write each entry. Returns {year_yy: max_number_observed}."""
    max_by_year: dict[int, int] = {}

    for entry in entries:
        code = entry["approval_code"]
        yy, num = parse_code(code)
        max_by_year[yy] = max(max_by_year.get(yy, 0), num)

        if dry_run:
            print(f"[DRY] document-records/{code} — {entry['title']}")
            continue

        ref = db.collection(RECORDS_COLLECTION).document(code)
        ref.set(build_record(entry))
        print(f"[OK]  document-records/{code} — {entry['title']}")

    return max_by_year


def advance_counters(db: firestore.Client | None, max_by_year: dict[int, int], dry_run: bool) -> None:
    """Advance document_counters/material-approval-{YYYY} for each observed year."""
    for yy, max_num in max_by_year.items():
        year = 2000 + yy
        doc_id = f"material-approval-{year}"

        if dry_run:
            print(f"[DRY] document_counters/{doc_id} -> last_number>={max_num}")
            continue

        assert db is not None
        ref = db.collection(COUNTERS_COLLECTION).document(doc_id)
        snap = ref.get()
        current = snap.to_dict().get("last_number", 0) if snap.exists else 0
        new_last = max(current, max_num)

        ref.set({
            "document_type": "material-approval",
            "prefix": "MA",
            "year": year,
            "last_number": new_last,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        print(f"[OK]  document_counters/{doc_id} -> last_number={new_last} (was {current})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print intended writes without touching Firestore.")
    args = parser.parse_args()

    if not SEED_PATH.exists():
        print(f"[ERR] Seed file not found: {SEED_PATH}", file=sys.stderr)
        return 1

    with SEED_PATH.open("r", encoding="utf-8") as f:
        seed = json.load(f)
    entries = seed.get("entries", [])
    if not entries:
        print("[ERR] Seed file has no entries.", file=sys.stderr)
        return 1

    codes = [e["approval_code"] for e in entries]
    if len(set(codes)) != len(codes):
        dupes = {c for c in codes if codes.count(c) > 1}
        print(f"[ERR] Duplicate approval codes in seed: {sorted(dupes)}", file=sys.stderr)
        return 1

    db = None if args.dry_run else get_db()
    if db:
        print(f"Connected to Firestore database: {DATABASE}\n")
        ensure_template(db)
    else:
        print("[DRY] Dry run — no Firestore writes will occur.\n")

    max_by_year = push_entries(db, entries, dry_run=args.dry_run)
    advance_counters(db, max_by_year, dry_run=args.dry_run)

    print(f"\n{'Would write' if args.dry_run else 'Wrote'} {len(entries)} records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
