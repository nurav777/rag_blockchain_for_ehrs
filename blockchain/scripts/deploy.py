from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import (
    load_dotenv,
    set_key,
)
from solcx import (
    compile_source,
    get_installed_solc_versions,
    install_solc,
)
from web3 import Web3


# ============================================================
# PATHS
# ============================================================


SCRIPT_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

BLOCKCHAIN_DIR = (
    SCRIPT_DIR
    .parent
)

PROJECT_ROOT = (
    BLOCKCHAIN_DIR
    .parent
)

CONTRACT_PATH = (
    BLOCKCHAIN_DIR
    / "contracts"
    / "MedicalRecordRegistry.sol"
)

ABI_PATH = (
    BLOCKCHAIN_DIR
    / "abi"
    / "MedicalRecordRegistry.json"
)

ENV_PATH = (
    PROJECT_ROOT
    / ".env"
)

ENV_EXAMPLE_PATH = (
    PROJECT_ROOT
    / ".env.example"
)


# ============================================================
# CONSTANTS
# ============================================================


SOLC_VERSION = "0.8.20"

#
# IMPORTANT:
#
# The current Besu genesis activates Berlin:
#
#     "berlinBlock": 0
#
# Solidity 0.8.20 otherwise defaults to a newer EVM target and
# may emit opcodes such as PUSH0, which Berlin does not support.
#

EVM_VERSION = "berlin"

DEFAULT_RPC_URL = (
    "http://127.0.0.1:8545"
)


# ============================================================
# ENVIRONMENT
# ============================================================


def ensure_env_file() -> None:
    """
    Create .env from .env.example if necessary.
    """

    if ENV_PATH.exists():
        return

    if not ENV_EXAMPLE_PATH.exists():
        raise RuntimeError(
            (
                ".env does not exist and "
                ".env.example could not be found"
            )
        )

    ENV_PATH.write_text(
        ENV_EXAMPLE_PATH.read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    print(
        f"Created {ENV_PATH} from .env.example"
    )


# ============================================================
# SOLIDITY COMPILER
# ============================================================


def ensure_solc() -> None:
    """
    Install Solidity compiler 0.8.20 when necessary.
    """

    installed = {
        str(version)
        for version in (
            get_installed_solc_versions()
        )
    }

    if SOLC_VERSION in installed:
        return

    print(
        f"Installing solc {SOLC_VERSION}..."
    )

    install_solc(
        SOLC_VERSION
    )


# ============================================================
# COMPILE CONTRACT
# ============================================================


def compile_contract() -> tuple[
    list[dict],
    str,
]:
    """
    Compile MedicalRecordRegistry.sol specifically for the
    Berlin EVM used by our current Besu genesis.
    """

    if not CONTRACT_PATH.exists():
        raise RuntimeError(
            (
                "Contract source not found: "
                f"{CONTRACT_PATH}"
            )
        )

    source = CONTRACT_PATH.read_text(
        encoding="utf-8"
    )

    ensure_solc()

    print(
        "Compiling MedicalRecordRegistry.sol..."
    )

    print(
        f"Solidity compiler: {SOLC_VERSION}"
    )

    print(
        f"EVM target: {EVM_VERSION}"
    )

    compiled = compile_source(
        source,
        output_values=[
            "abi",
            "bin",
        ],
        solc_version=SOLC_VERSION,

        #
        # Critical for this Besu network.
        #
        evm_version=EVM_VERSION,
    )

    contract_key = (
        "<stdin>:"
        "MedicalRecordRegistry"
    )

    if contract_key not in compiled:
        raise RuntimeError(
            (
                "Compiled output did not contain "
                "MedicalRecordRegistry"
            )
        )

    interface = compiled[
        contract_key
    ]

    abi = interface[
        "abi"
    ]

    bytecode = interface[
        "bin"
    ]

    if not bytecode:
        raise RuntimeError(
            "Compiled contract bytecode is empty"
        )

    print(
        (
            "Compiled deployment bytecode size: "
            f"{len(bytecode) // 2} bytes"
        )
    )

    return (
        abi,
        bytecode,
    )


# ============================================================
# SAVE ABI
# ============================================================


def save_abi(
    abi: list[dict],
) -> None:
    """
    Save the ABI generated from the exact contract being deployed.
    """

    ABI_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ABI_PATH.write_text(
        json.dumps(
            abi,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"ABI written to {ABI_PATH}"
    )


# ============================================================
# WEB3
# ============================================================


def connect_web3(
    rpc_url: str,
) -> Web3:
    """
    Connect to the Besu RPC endpoint.
    """

    web3 = Web3(
        Web3.HTTPProvider(
            rpc_url
        )
    )

    if not web3.is_connected():
        raise RuntimeError(
            (
                "Unable to connect to Besu at "
                f"{rpc_url}"
            )
        )

    return web3


# ============================================================
# DEPLOYER
# ============================================================


def get_or_create_deployer_key(
    web3: Web3,
) -> str:
    """
    Reuse the development deployer key stored in .env.

    If none exists, generate one and save it.

    Our local Besu network accepts zero-gas-price transactions,
    so this development account does not need normal ETH funding.
    """

    existing_key = (
        os.getenv(
            "DEPLOYER_PRIVATE_KEY",
            "",
        )
        .strip()
    )

    if existing_key:
        try:
            account = (
                web3.eth.account.from_key(
                    existing_key
                )
            )

        except Exception as exc:
            raise RuntimeError(
                (
                    "DEPLOYER_PRIVATE_KEY "
                    "in .env is invalid"
                )
            ) from exc

        print(
            (
                "Using existing deployer: "
                f"{account.address}"
            )
        )

        return existing_key

    account = (
        web3.eth.account.create()
    )

    private_key = (
        account.key.hex()
    )

    if not private_key.startswith(
        "0x"
    ):
        private_key = (
            f"0x{private_key}"
        )

    set_key(
        str(ENV_PATH),
        "DEPLOYER_PRIVATE_KEY",
        private_key,
    )

    os.environ[
        "DEPLOYER_PRIVATE_KEY"
    ] = private_key

    print(
        (
            "Generated local development "
            f"deployer: {account.address}"
        )
    )

    print(
        "DEPLOYER_PRIVATE_KEY saved to .env"
    )

    return private_key


# ============================================================
# DEPLOY CONTRACT
# ============================================================


def deploy_contract(
    web3: Web3,
    abi: list[dict],
    bytecode: str,
    private_key: str,
) -> str:
    """
    Deploy MedicalRecordRegistry.
    """

    account = (
        web3.eth.account.from_key(
            private_key
        )
    )

    contract = (
        web3.eth.contract(
            abi=abi,
            bytecode=bytecode,
        )
    )

    nonce = (
        web3.eth.get_transaction_count(
            account.address
        )
    )

    chain_id = (
        web3.eth.chain_id
    )

    print(
        f"Besu chain ID: {chain_id}"
    )

    print(
        (
            "Deploying from account: "
            f"{account.address}"
        )
    )

    print(
        f"Account nonce: {nonce}"
    )

    #
    # Estimate gas first.
    #
    # This also gives us an earlier and clearer failure if the
    # bytecode is incompatible with the active EVM.
    #
    try:
        estimated_gas = (
            contract
            .constructor()
            .estimate_gas(
                {
                    "from": (
                        account.address
                    ),
                }
            )
        )

    except Exception as exc:
        raise RuntimeError(
            (
                "Contract gas estimation failed. "
                "The bytecode may be incompatible "
                "with the Besu EVM configuration. "
                f"Original error: {exc}"
            )
        ) from exc

    #
    # Add some headroom above the estimate.
    #
    gas_limit = int(
        estimated_gas * 1.25
    )

    print(
        (
            "Estimated deployment gas: "
            f"{estimated_gas}"
        )
    )

    print(
        (
            "Deployment gas limit: "
            f"{gas_limit}"
        )
    )

    transaction = (
        contract
        .constructor()
        .build_transaction(
            {
                "from": account.address,
                "nonce": nonce,
                "chainId": chain_id,
                "gas": gas_limit,
                "gasPrice": 0,
            }
        )
    )

    signed = (
        account.sign_transaction(
            transaction
        )
    )

    tx_hash = (
        web3.eth.send_raw_transaction(
            signed.raw_transaction
        )
    )

    tx_hash_hex = (
        tx_hash.hex()
    )

    if not tx_hash_hex.startswith(
        "0x"
    ):
        tx_hash_hex = (
            f"0x{tx_hash_hex}"
        )

    print(
        (
            "Deployment transaction: "
            f"{tx_hash_hex}"
        )
    )

    print(
        "Waiting for deployment receipt..."
    )

    receipt = (
        web3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=120,
        )
    )

    print(
        f"Receipt status: {receipt.status}"
    )

    print(
        f"Gas used: {receipt.gasUsed}"
    )

    print(
        f"Block number: {receipt.blockNumber}"
    )

    if receipt.status != 1:
        raise RuntimeError(
            (
                "Contract deployment transaction "
                "was mined but EVM execution failed"
            )
        )

    contract_address = (
        receipt.contractAddress
    )

    if not contract_address:
        raise RuntimeError(
            (
                "Deployment succeeded but the "
                "receipt contains no contract address"
            )
        )

    return (
        Web3.to_checksum_address(
            contract_address
        )
    )


# ============================================================
# SAVE ADDRESS
# ============================================================


def save_contract_address(
    contract_address: str,
) -> None:
    """
    Save the new deployment address into .env.
    """

    set_key(
        str(ENV_PATH),
        "CONTRACT_ADDRESS",
        contract_address,
    )

    os.environ[
        "CONTRACT_ADDRESS"
    ] = contract_address

    print(
        "CONTRACT_ADDRESS saved to .env"
    )


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    print(
        "========================================"
    )

    print(
        " MedicalRecordRegistry Deployment"
    )

    print(
        "========================================"
    )

    ensure_env_file()

    load_dotenv(
        ENV_PATH,
        override=True,
    )

    rpc_url = (
        os.getenv(
            "BESU_RPC_URL",
            DEFAULT_RPC_URL,
        )
        .strip()
        or DEFAULT_RPC_URL
    )

    print(
        f"Connecting to Besu: {rpc_url}"
    )

    web3 = connect_web3(
        rpc_url
    )

    print(
        (
            "Connected. Current block: "
            f"{web3.eth.block_number}"
        )
    )

    abi, bytecode = (
        compile_contract()
    )

    save_abi(
        abi
    )

    private_key = (
        get_or_create_deployer_key(
            web3
        )
    )

    contract_address = (
        deploy_contract(
            web3=web3,
            abi=abi,
            bytecode=bytecode,
            private_key=private_key,
        )
    )

    save_contract_address(
        contract_address
    )

    print()

    print(
        "========================================"
    )

    print(
        " Deployment successful"
    )

    print(
        "========================================"
    )

    print(
        (
            "Contract address: "
            f"{contract_address}"
        )
    )

    print(
        (
            "ABI: "
            f"{ABI_PATH}"
        )
    )

    print(
        (
            "Environment: "
            f"{ENV_PATH}"
        )
    )

    print(
        "========================================"
    )


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print(
            "\nDeployment cancelled."
        )

        sys.exit(1)

    except Exception as exc:
        print()

        print(
            "Deployment failed:"
        )

        print(
            str(exc)
        )

        sys.exit(1)