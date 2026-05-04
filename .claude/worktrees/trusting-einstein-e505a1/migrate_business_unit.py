"""Tag every existing document and template in go-documents with a business_unit.

Default behavior: tag every record in `document-templates` and `document-records`
with `business_unit = "Leka Studio"` UNLESS the document already has a
business_unit set.

Idempotent — re-running is safe.

Usage:
    python migrate_business_unit.py [--dry-run] [--default "Leka Studio"]
"""

import argparse
import os
import sys
from datetime import datetime, timezone

from google.cloud import firestore

DATABASE = "go-documents"
DEFAULT_UNIT = "Leka Studio"
TARGET_COLLECTIONS = ["document-templates", "document-records"]

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


def migrate_collection(db: firestore.Client | None, coll_name: str, default: str, dry_run: bool) -> tuple[int, int, int]:
    """Return (tagged_new, already_set, total)."""
    tagged = 0
    already = 0
    total = 0

    if dry_run and db is None:
        print(f"[DRY] Would scan collection: {coll_name}")
        return 0, 0, 0

    assert db is not None
    for doc in db.collection(coll_name).stream():
        total += 1
        data = doc.to_dict() or {}
        current = data.get("business_unit")
        if current:
            already += 1
            print(f"[--] {coll_name}/{doc.id}: business_unit already = {current!r}")
            continue

        now = datetime.now(timezone.utc).isoformat()
        payload = {"business_unit": default, "updated_at": now}
        if dry_run:
            print(f"[DRY] {coll_name}/{doc.id}: set business_unit -> {default!r}")
        else:
            doc.reference.set(payload, merge=True)
            print(f"[OK]  {coll_name}/{doc.id}: set business_unit -> {default!r}")
        tagged += 1

    return tagged, already, total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print intended writes without touching Firestore.")
    parser.add_argument("--default", default=DEFAULT_UNIT, help=f"Business unit to assign when missing (default: {DEFAULT_UNIT!r}).")
    args = parser.parse_args()

    db = None if args.dry_run else get_db()
    if db:
        print(f"Connected to Firestore database: {DATABASE}\n")
    else:
        print("[DRY] Dry run — no Firestore writes.\n")

    grand_tagged = grand_already = grand_total = 0
    for coll in TARGET_COLLECTIONS:
        print(f"--- {coll} ---")
        tagged, already, total = migrate_collection(db, coll, args.default, args.dry_run)
        grand_tagged += tagged
        grand_already += already
        grand_total += total
        print(f"    tagged={tagged}  already_set={already}  total={total}\n")

    print(f"Summary: tagged={grand_tagged}, already_set={grand_already}, total={grand_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
