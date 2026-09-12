# Blockchain (Hyperledger Besu)

Local QBFT consortium network used for record-reference integrity and clinician-wallet authorization. Medical PDFs are never stored on-chain.

## Record registry

The current `MedicalRecordRegistry` stores:

- SHA-256 record hash
- IPFS CID
- uploader clinician wallet
- block timestamp

It also stores an allow-list of clinician wallets. The deployer is the contract owner and is authorized automatically.

Deploy:

```powershell
python blockchain/scripts/deploy.py
```

Authorize another clinician wallet:

```powershell
python scripts/authorize_wallet.py 0xYOUR_WALLET_ADDRESS
```

The backend prototype relays record registration using the contract-owner deployer key after the clinician has authenticated by signing a wallet challenge. The contract also exposes direct wallet registration for a future frontend that submits transactions itself.

## Network

- Chain ID: `1337`
- Consensus: QBFT
- RPC: `http://127.0.0.1:8545`
- Validator nodes: `hospital-a`, `hospital-b`, `hospital-c`

Start:

```powershell
cd blockchain
docker compose up -d
```

Stop:

```powershell
docker compose down
```

Validator keys included here are local-development keys only.
