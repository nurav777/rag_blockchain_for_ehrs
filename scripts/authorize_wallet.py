from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.blockchain_service import BlockchainError, blockchain_service  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Authorize or revoke a clinician wallet.")
    parser.add_argument("wallet_address")
    parser.add_argument(
        "--revoke",
        action="store_true",
        help="Revoke instead of authorize.",
    )
    args = parser.parse_args()

    authorized = not args.revoke
    try:
        tx_hash = blockchain_service.set_clinician_authorization(
            args.wallet_address,
            authorized,
        )
    except BlockchainError as exc:
        raise SystemExit(exc.message) from exc

    action = "authorized" if authorized else "revoked"
    print(f"Wallet {action}: {args.wallet_address}")
    print(f"Transaction: {tx_hash}")


if __name__ == "__main__":
    main()
