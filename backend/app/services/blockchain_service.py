from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.contract import Contract

from app.config import PROJECT_ROOT, settings


logger = logging.getLogger(__name__)


class BlockchainError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class BlockchainService:
    """Interaction layer for the wallet-based MedicalRecordRegistry."""

    def is_configured(self) -> bool:
        return bool(settings.BESU_RPC_URL and settings.CONTRACT_ADDRESS)

    def can_write(self) -> bool:
        return bool(self.is_configured() and settings.blockchain_relayer_private_key)

    def register_record(
        self,
        *,
        record_hash: str,
        ipfs_cid: str,
        uploader_wallet: str,
    ) -> str:
        if not self.can_write():
            raise BlockchainError("Blockchain relayer credentials are not configured")

        normalized_hash = self._normalize_hash(record_hash)
        if not ipfs_cid.strip():
            raise BlockchainError("IPFS CID cannot be empty")

        try:
            uploader = Web3.to_checksum_address(uploader_wallet)
        except Exception as exc:
            raise BlockchainError("Invalid uploader wallet address") from exc

        web3 = self._get_web3()
        contract = self._get_contract(web3)

        if not self.is_authorized_clinician(uploader):
            raise BlockchainError("Uploader wallet is not an authorized clinician")

        try:
            account = web3.eth.account.from_key(settings.blockchain_relayer_private_key)
            transaction = contract.functions.registerRecordFor(
                self._hash_to_bytes32(normalized_hash),
                ipfs_cid,
                uploader,
            ).build_transaction(
                {
                    "from": account.address,
                    "nonce": web3.eth.get_transaction_count(account.address),
                    "gas": 700_000,
                    "gasPrice": web3.eth.gas_price,
                    "chainId": web3.eth.chain_id,
                }
            )
            signed = account.sign_transaction(transaction)
            tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        except Exception as exc:
            raise BlockchainError("Failed to register medical record on blockchain") from exc

        if receipt.status != 1:
            raise BlockchainError("registerRecordFor transaction failed")

        value = tx_hash.hex()
        return value if value.startswith("0x") else f"0x{value}"

    def get_record(self, record_hash: str) -> dict[str, Any]:
        if not self.is_configured():
            raise BlockchainError("Blockchain service is not configured")

        normalized_hash = self._normalize_hash(record_hash)
        contract = self._get_contract(self._get_web3())

        try:
            result = contract.functions.getRecord(
                self._hash_to_bytes32(normalized_hash)
            ).call()
        except Exception as exc:
            raise BlockchainError(f"Blockchain record not found: {normalized_hash}") from exc

        if len(result) != 4:
            raise BlockchainError("Unexpected response returned by smart contract")

        return {
            "record_hash": self._bytes32_to_hash(result[0]),
            "ipfs_cid": result[1],
            "uploader_wallet": Web3.to_checksum_address(result[2]),
            "timestamp": int(result[3]),
        }

    def verify_record_hash(self, record_hash: str) -> bool:
        if not self.is_configured():
            raise BlockchainError("Blockchain service is not configured")

        try:
            return bool(
                self._get_contract(self._get_web3()).functions.verifyRecord(
                    self._hash_to_bytes32(self._normalize_hash(record_hash))
                ).call()
            )
        except Exception:
            return False

    def is_authorized_clinician(self, wallet_address: str) -> bool:
        if not self.is_configured():
            raise BlockchainError("Blockchain service is not configured")

        try:
            wallet = Web3.to_checksum_address(wallet_address)
            return bool(
                self._get_contract(self._get_web3()).functions.isClinician(wallet).call()
            )
        except Exception as exc:
            raise BlockchainError("Unable to check clinician wallet authorization") from exc

    def set_clinician_authorization(self, wallet_address: str, authorized: bool) -> str:
        if not self.can_write():
            raise BlockchainError("Blockchain relayer credentials are not configured")

        try:
            wallet = Web3.to_checksum_address(wallet_address)
        except Exception as exc:
            raise BlockchainError("Invalid clinician wallet address") from exc

        web3 = self._get_web3()
        contract = self._get_contract(web3)
        account = web3.eth.account.from_key(settings.blockchain_relayer_private_key)

        try:
            transaction = contract.functions.setClinician(wallet, authorized).build_transaction(
                {
                    "from": account.address,
                    "nonce": web3.eth.get_transaction_count(account.address),
                    "gas": 300_000,
                    "gasPrice": web3.eth.gas_price,
                    "chainId": web3.eth.chain_id,
                }
            )
            signed = account.sign_transaction(transaction)
            tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        except Exception as exc:
            raise BlockchainError("Failed to update clinician authorization") from exc

        if receipt.status != 1:
            raise BlockchainError("setClinician transaction failed")

        value = tx_hash.hex()
        return value if value.startswith("0x") else f"0x{value}"

    def relayer_wallet_address(self) -> str:
        if not settings.blockchain_relayer_private_key:
            raise BlockchainError("Blockchain relayer private key is not configured")
        try:
            return self._get_web3().eth.account.from_key(
                settings.blockchain_relayer_private_key
            ).address
        except Exception as exc:
            raise BlockchainError("Invalid blockchain relayer private key") from exc

    def _load_contract_abi(self) -> list[dict[str, Any]]:
        abi_path = Path(settings.CONTRACT_ABI_PATH)
        if not abi_path.is_absolute():
            abi_path = (PROJECT_ROOT / abi_path).resolve()
        if not abi_path.exists():
            raise BlockchainError(f"Contract ABI not found at {abi_path}")
        try:
            abi = json.loads(abi_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BlockchainError(f"Unable to read contract ABI from {abi_path}") from exc
        if not isinstance(abi, list):
            raise BlockchainError("Contract ABI must be a JSON array")
        return abi

    def _get_contract(self, web3: Web3) -> Contract:
        if not settings.CONTRACT_ADDRESS:
            raise BlockchainError("Contract address is not configured")
        try:
            address = Web3.to_checksum_address(settings.CONTRACT_ADDRESS)
        except Exception as exc:
            raise BlockchainError("Invalid smart-contract address") from exc
        return web3.eth.contract(address=address, abi=self._load_contract_abi())

    def _get_web3(self) -> Web3:
        web3 = Web3(Web3.HTTPProvider(settings.BESU_RPC_URL))
        try:
            connected = web3.is_connected()
        except Exception as exc:
            raise BlockchainError("Unable to contact Besu node") from exc
        if not connected:
            raise BlockchainError(f"Unable to connect to Besu node at {settings.BESU_RPC_URL}")
        return web3

    def _normalize_hash(self, record_hash: str) -> str:
        if not isinstance(record_hash, str):
            raise BlockchainError("Record hash must be a string")
        normalized = record_hash.strip().lower().removeprefix("0x")
        if len(normalized) != 64:
            raise BlockchainError("Record hash must be a 32-byte SHA-256 hex string")
        try:
            bytes.fromhex(normalized)
        except ValueError as exc:
            raise BlockchainError("Record hash must contain only hexadecimal characters") from exc
        return normalized

    def _hash_to_bytes32(self, record_hash: str) -> bytes:
        return bytes.fromhex(self._normalize_hash(record_hash))

    def _bytes32_to_hash(self, value: Any) -> str:
        hex_value = value.hex() if hasattr(value, "hex") else bytes(value).hex()
        normalized = hex_value.lower().removeprefix("0x")
        if len(normalized) != 64:
            raise BlockchainError("Blockchain returned an invalid record hash")
        return normalized


blockchain_service = BlockchainService()
