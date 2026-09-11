from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.contract import Contract

from app.config import PROJECT_ROOT, settings


logger = logging.getLogger(__name__)


HOSPITAL_CHAIN_IDS: dict[str, int] = {
    "hospital_a": 1,
    "hospital_b": 2,
    "hospital_c": 3,
}


class BlockchainError(Exception):
    """
    Raised when an operation involving the blockchain cannot be completed.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class BlockchainService:
    """
    Service responsible for communication with the
    MedicalRecordRegistry smart contract.

    Medical records are identified by their SHA-256 hash.

    No SQL/database medical-record ID is used by this service.
    """

    # =========================================================
    # CONFIGURATION
    # =========================================================

    def is_configured(self) -> bool:
        """
        Return True when enough configuration exists to interact
        with the blockchain.

        This does not guarantee that the Besu node is reachable.
        """

        return bool(
            settings.BESU_RPC_URL
            and settings.CONTRACT_ADDRESS
            and settings.DEPLOYER_PRIVATE_KEY
        )

    # =========================================================
    # REGISTER RECORD
    # =========================================================

    def register_record(
        self,
        record_hash: str,
        ipfs_cid: str,
        doctor_id: int,
        hospital_id: str,
    ) -> str:
        """
        Register a medical record on-chain.

        The SHA-256 hash is the record identifier.

        Returns:
            Transaction hash as a 0x-prefixed hexadecimal string.
        """

        if not self.is_configured():
            raise BlockchainError(
                "Blockchain credentials are not configured"
            )

        normalized_hash = self._normalize_hash(record_hash)

        if not ipfs_cid.strip():
            raise BlockchainError(
                "IPFS CID cannot be empty"
            )

        web3 = self._get_web3()
        contract = self._get_contract(web3)

        try:
            account = web3.eth.account.from_key(
                settings.DEPLOYER_PRIVATE_KEY
            )
        except Exception as exc:
            raise BlockchainError(
                "Invalid blockchain deployer private key"
            ) from exc

        hospital_chain_id = self._hospital_id_to_chain_id(
            hospital_id
        )

        try:
            transaction = (
                contract.functions.registerRecord(
                    self._hash_to_bytes32(normalized_hash),
                    ipfs_cid,
                    doctor_id,
                    hospital_chain_id,
                )
                .build_transaction(
                    {
                        "from": account.address,
                        "nonce": web3.eth.get_transaction_count(
                            account.address
                        ),
                        "gas": 600_000,
                        "gasPrice": web3.eth.gas_price,
                        "chainId": web3.eth.chain_id,
                    }
                )
            )

            signed = account.sign_transaction(
                transaction
            )

            tx_hash = web3.eth.send_raw_transaction(
                signed.raw_transaction
            )

            receipt = web3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=120,
            )

        except Exception as exc:
            raise BlockchainError(
                "Failed to register medical record on blockchain"
            ) from exc

        if receipt.status != 1:
            raise BlockchainError(
                "registerRecord transaction failed"
            )

        tx_hash_hex = tx_hash.hex()

        if not tx_hash_hex.startswith("0x"):
            tx_hash_hex = f"0x{tx_hash_hex}"

        logger.info(
            "Registered medical record %s on blockchain "
            "with transaction %s",
            normalized_hash,
            tx_hash_hex,
        )

        return tx_hash_hex

    # =========================================================
    # GET RECORD
    # =========================================================

    def get_record(
        self,
        record_hash: str,
    ) -> dict[str, Any]:
        """
        Retrieve a medical-record reference from the blockchain.

        Returns:
            {
                "record_hash": "...",
                "ipfs_cid": "...",
                "doctor_id": 1,
                "hospital_id": 1,
                "timestamp": 123456789
            }
        """

        if not self.is_configured():
            raise BlockchainError(
                "Blockchain credentials are not configured"
            )

        normalized_hash = self._normalize_hash(
            record_hash
        )

        web3 = self._get_web3()
        contract = self._get_contract(web3)

        try:
            result = (
                contract.functions.getRecord(
                    self._hash_to_bytes32(
                        normalized_hash
                    )
                )
                .call()
            )

        except Exception as exc:
            logger.warning(
                "Unable to retrieve blockchain record %s: %s",
                normalized_hash,
                exc,
            )

            raise BlockchainError(
                f"Blockchain record not found: "
                f"{normalized_hash}"
            ) from exc

        if len(result) != 5:
            raise BlockchainError(
                "Unexpected response returned by smart contract"
            )

        on_chain_hash = self._bytes32_to_hash(
            result[0]
        )

        return {
            "record_hash": on_chain_hash,
            "ipfs_cid": result[1],
            "doctor_id": int(result[2]),
            "hospital_id": int(result[3]),
            "timestamp": int(result[4]),
        }

    # =========================================================
    # VERIFY RECORD
    # =========================================================

    def verify_record_hash(
        self,
        record_hash: str,
    ) -> bool:
        """
        Return True when the supplied record hash exists
        in the smart contract registry.
        """

        if not self.is_configured():
            raise BlockchainError(
                "Blockchain credentials are not configured"
            )

        normalized_hash = self._normalize_hash(
            record_hash
        )

        web3 = self._get_web3()
        contract = self._get_contract(web3)

        try:
            return bool(
                contract.functions.verifyRecord(
                    self._hash_to_bytes32(
                        normalized_hash
                    )
                )
                .call()
            )

        except Exception as exc:
            logger.warning(
                "Blockchain verification failed for %s: %s",
                normalized_hash,
                exc,
            )

            return False

    # =========================================================
    # CONTRACT
    # =========================================================

    def _load_contract_abi(
        self,
    ) -> list[dict[str, Any]]:
        """
        Load the MedicalRecordRegistry ABI from disk.
        """

        abi_path = Path(
            settings.CONTRACT_ABI_PATH
        )

        if not abi_path.is_absolute():
            abi_path = (
                PROJECT_ROOT / abi_path
            ).resolve()

        if not abi_path.exists():
            raise BlockchainError(
                f"Contract ABI not found at {abi_path}"
            )

        try:
            with abi_path.open(
                encoding="utf-8"
            ) as abi_file:
                abi = json.load(
                    abi_file
                )

        except (OSError, json.JSONDecodeError) as exc:
            raise BlockchainError(
                f"Unable to read contract ABI from "
                f"{abi_path}"
            ) from exc

        if not isinstance(abi, list):
            raise BlockchainError(
                "Contract ABI must be a JSON array"
            )

        return abi

    def _get_contract(
        self,
        web3: Web3,
    ) -> Contract:
        """
        Create a Web3 contract instance.
        """

        if not settings.CONTRACT_ADDRESS:
            raise BlockchainError(
                "Contract address is not configured"
            )

        try:
            contract_address = (
                Web3.to_checksum_address(
                    settings.CONTRACT_ADDRESS
                )
            )

        except ValueError as exc:
            raise BlockchainError(
                "Invalid smart-contract address"
            ) from exc

        return web3.eth.contract(
            address=contract_address,
            abi=self._load_contract_abi(),
        )

    # =========================================================
    # WEB3
    # =========================================================

    def _get_web3(
        self,
    ) -> Web3:
        """
        Connect to the configured Hyperledger Besu node.
        """

        web3 = Web3(
            Web3.HTTPProvider(
                settings.BESU_RPC_URL
            )
        )

        try:
            connected = web3.is_connected()

        except Exception as exc:
            raise BlockchainError(
                "Unable to contact Besu node"
            ) from exc

        if not connected:
            raise BlockchainError(
                f"Unable to connect to Besu node at "
                f"{settings.BESU_RPC_URL}"
            )

        return web3

    # =========================================================
    # HOSPITAL MAPPING
    # =========================================================

    def _hospital_id_to_chain_id(
        self,
        hospital_id: str,
    ) -> int:
        """
        Convert application hospital IDs into their
        numeric blockchain representation.
        """

        chain_id = HOSPITAL_CHAIN_IDS.get(
            hospital_id
        )

        if chain_id is None:
            raise BlockchainError(
                f"Unsupported hospital ID: "
                f"{hospital_id}"
            )

        return chain_id

    # =========================================================
    # HASH UTILITIES
    # =========================================================

    def _normalize_hash(
        self,
        record_hash: str,
    ) -> str:
        """
        Validate and normalize a SHA-256 hexadecimal hash.
        """

        if not isinstance(
            record_hash,
            str,
        ):
            raise BlockchainError(
                "Record hash must be a string"
            )

        normalized = (
            record_hash
            .strip()
            .lower()
            .removeprefix("0x")
        )

        if len(normalized) != 64:
            raise BlockchainError(
                "Record hash must be a "
                "32-byte SHA-256 hex string"
            )

        try:
            bytes.fromhex(
                normalized
            )

        except ValueError as exc:
            raise BlockchainError(
                "Record hash must contain only "
                "hexadecimal characters"
            ) from exc

        return normalized

    def _hash_to_bytes32(
        self,
        record_hash: str,
    ) -> bytes:
        """
        Convert a SHA-256 hexadecimal string into bytes32.
        """

        normalized = self._normalize_hash(
            record_hash
        )

        return bytes.fromhex(
            normalized
        )

    def _bytes32_to_hash(
        self,
        value: Any,
    ) -> str:
        """
        Convert a Solidity bytes32 result into a
        normalized SHA-256 hexadecimal string.
        """

        if hasattr(
            value,
            "hex",
        ):
            hex_value = value.hex()
        else:
            hex_value = bytes(
                value
            ).hex()

        normalized = (
            hex_value
            .lower()
            .removeprefix("0x")
        )

        if len(normalized) != 64:
            raise BlockchainError(
                "Blockchain returned an invalid "
                "record hash"
            )

        return normalized


blockchain_service = BlockchainService()