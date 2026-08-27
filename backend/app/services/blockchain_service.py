import json
import logging
from pathlib import Path

from web3 import Web3

from app.config import PROJECT_ROOT, settings

logger = logging.getLogger(__name__)

HOSPITAL_CHAIN_IDS = {
    "hospital_a": 1,
    "hospital_b": 2,
    "hospital_c": 3,
}


class BlockchainError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class BlockchainService:
    def is_configured(self) -> bool:
        return bool(
            settings.BESU_RPC_URL
            and settings.CONTRACT_ADDRESS
            and settings.DEPLOYER_PRIVATE_KEY
        )

    def register_record(
        self,
        record_id: int,
        record_hash: str,
        ipfs_cid: str,
        doctor_id: int,
        hospital_id: str,
    ) -> str:
        if not self.is_configured():
            raise BlockchainError("Blockchain credentials are not configured")

        web3 = self._get_web3()
        contract = self._get_contract(web3)
        account = web3.eth.account.from_key(settings.DEPLOYER_PRIVATE_KEY)
        hospital_chain_id = self._hospital_id_to_chain_id(hospital_id)

        transaction = contract.functions.registerRecord(
            record_id,
            self._hash_to_bytes32(record_hash),
            ipfs_cid,
            doctor_id,
            hospital_chain_id,
        ).build_transaction(
            {
                "from": account.address,
                "nonce": web3.eth.get_transaction_count(account.address),
                "gas": 600_000,
                "gasPrice": web3.eth.gas_price,
                "chainId": web3.eth.chain_id,
            }
        )

        signed = account.sign_transaction(transaction)
        tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.status != 1:
            raise BlockchainError(f"registerRecord transaction failed: {tx_hash.hex()}")

        tx_hash_hex = tx_hash.hex()
        if not tx_hash_hex.startswith("0x"):
            tx_hash_hex = f"0x{tx_hash_hex}"

        logger.info(
            "Registered record %s on blockchain with transaction %s",
            record_id,
            tx_hash_hex,
        )
        return tx_hash_hex

    def verify_record_hash(self, record_id: int, record_hash: str) -> bool:
        if not self.is_configured():
            raise BlockchainError("Blockchain credentials are not configured")

        web3 = self._get_web3()
        contract = self._get_contract(web3)

        try:
            on_chain = contract.functions.getRecord(record_id).call()
        except Exception as exc:
            logger.warning("getRecord failed for record %s: %s", record_id, exc)
            return False

        on_chain_hash = on_chain[1]
        if hasattr(on_chain_hash, "hex"):
            on_chain_hex = on_chain_hash.hex().removeprefix("0x")
        else:
            on_chain_hex = bytes(on_chain_hash).hex()
        return on_chain_hex.lower() == record_hash.removeprefix("0x").lower()

    def _load_contract_abi(self) -> list:
        abi_path = Path(settings.CONTRACT_ABI_PATH)
        if not abi_path.is_absolute():
            abi_path = PROJECT_ROOT / abi_path
        if not abi_path.exists():
            raise BlockchainError(f"Contract ABI not found at {abi_path}")

        with abi_path.open(encoding="utf-8") as abi_file:
            return json.load(abi_file)

    def _get_web3(self) -> Web3:
        web3 = Web3(Web3.HTTPProvider(settings.BESU_RPC_URL))
        if not web3.is_connected():
            raise BlockchainError(f"Unable to connect to Besu node at {settings.BESU_RPC_URL}")
        return web3

    def _get_contract(self, web3: Web3):
        return web3.eth.contract(
            address=Web3.to_checksum_address(settings.CONTRACT_ADDRESS),
            abi=self._load_contract_abi(),
        )

    def _hospital_id_to_chain_id(self, hospital_id: str) -> int:
        chain_id = HOSPITAL_CHAIN_IDS.get(hospital_id)
        if chain_id is None:
            raise BlockchainError(f"Unsupported hospital ID: {hospital_id}")
        return chain_id

    def _hash_to_bytes32(self, record_hash: str) -> bytes:
        normalized = record_hash.removeprefix("0x")
        if len(normalized) != 64:
            raise BlockchainError("Record hash must be a 32-byte SHA-256 hex string")
        return bytes.fromhex(normalized)


blockchain_service = BlockchainService()
