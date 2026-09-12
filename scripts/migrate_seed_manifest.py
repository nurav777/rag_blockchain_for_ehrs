from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
MANIFEST_PATH = PROJECT_ROOT / "data" / "demo_seed_manifest.json"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.blockchain_service import BlockchainError, blockchain_service  # noqa: E402


def clean_entry(entry: dict[str, Any]) -> None:
    if "tx_hash" in entry and "legacy_tx_hash" not in entry:
        entry["legacy_tx_hash"] = entry.pop("tx_hash")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Re-register existing seeded record_hash → CID references in the new "
            "wallet-based registry without re-uploading IPFS content or rebuilding Chroma."
        )
    )
    parser.add_argument(
        "--wallet-address",
        default=None,
        help=(
            "Clinician wallet to attribute the migrated synthetic records to. "
            "Defaults to the configured relayer/deployer wallet."
        ),
    )
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        raise SystemExit(f"Manifest not found: {MANIFEST_PATH}")

    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    wallet = args.wallet_address or blockchain_service.relayer_wallet_address()

    if not blockchain_service.is_authorized_clinician(wallet):
        raise SystemExit(
            f"Wallet {wallet} is not an authorized clinician. "
            "Run scripts/authorize_wallet.py first."
        )

    records = data.get("records", [])
    migrated = 0
    skipped = 0
    failed = 0

    print(f"Migrating {len(records)} manifest records to wallet registry")
    print(f"Uploader wallet: {wallet}")

    for index, entry in enumerate(records, start=1):
        clean_entry(entry)
        record_hash = str(entry.get("record_hash", "")).strip()
        ipfs_cid = str(entry.get("ipfs_cid", "")).strip()

        if not record_hash or not ipfs_cid:
            failed += 1
            entry["v2_migration_error"] = "Missing record_hash or ipfs_cid"
            print(f"[{index:02d}/{len(records):02d}] missing reference FAILED")
            continue

        try:
            if blockchain_service.verify_record_hash(record_hash):
                skipped += 1
                entry["v2_blockchain_verified"] = True
                entry["uploader_wallet"] = wallet
                print(f"[{index:02d}/{len(records):02d}] {record_hash[:12]}... already registered")
                continue

            tx_hash = blockchain_service.register_record(
                record_hash=record_hash,
                ipfs_cid=ipfs_cid,
                uploader_wallet=wallet,
            )
            entry["v2_tx_hash"] = tx_hash
            entry["v2_blockchain_verified"] = True
            entry["uploader_wallet"] = wallet
            entry.pop("v2_migration_error", None)
            migrated += 1
            print(f"[{index:02d}/{len(records):02d}] {record_hash[:12]}... migrated")
        except BlockchainError as exc:
            failed += 1
            entry["v2_migration_error"] = exc.message
            print(f"[{index:02d}/{len(records):02d}] {record_hash[:12]}... FAILED: {exc.message}")

        MANIFEST_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    data["identity_model"] = "wallet"
    data["uploader_wallet"] = wallet
    data["migration_summary"] = {
        "migrated": migrated,
        "skipped": skipped,
        "failed": failed,
    }
    MANIFEST_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"Migrated: {migrated}; skipped: {skipped}; failed: {failed}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
