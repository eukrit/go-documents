"""Create Gmail labels `Submissions/Materials` and `Submissions/Drawings` on
eukrit@goco.bz via Domain-Wide Delegation. Idempotent.

Usage:
    python scripts/setup_gmail_labels.py

Requires:
    - ADC for `claude@ai-agents-go` (gcloud auth application-default login
      or running on Cloud Run/Cloud Shell).
    - DWD granted to the SA for scopes gmail.labels + gmail.modify.
"""
import sys

sys.path.insert(0, "src")

from gmail_sender import ensure_labels  # noqa: E402


def main():
    labels = ensure_labels()
    for name, lid in labels.items():
        print(f"  {name:30s} -> {lid}")
    print("OK")


if __name__ == "__main__":
    main()
