# Wallet-Authenticated Blockchain Medical Records RAG

Prototype architecture for secure medical-record discovery and retrieval using FastAPI, Hyperledger Besu, IPFS and RAG.

## Identity model

There is **no relational identity database**. The backend does not keep patient accounts, patient IDs, doctor IDs, emails or passwords.

A clinician proves control of an Ethereum-compatible wallet:

```text
wallet -> /api/auth/challenge -> sign message -> /api/auth/verify -> short-lived access token
```

The access token is only a session wrapper. The identity inside it is the verified wallet address. The wallet must also be authorized in the Besu smart contract.

## Record path

```text
authenticated clinician wallet
        |
        v
      PDF bytes
        |
        +--> SHA-256 record_hash
        +--> IPFS (Pinata only for prototype pinning) -> CID
        +--> Besu -> record_hash + CID + uploader_wallet
        +--> Chroma -> embedding + record_hash + chunk_index
```

Chroma intentionally stores no plaintext document and no patient identity metadata.

## Search path

```text
query -> embedding -> Chroma -> record_hash -> Besu -> CID -> IPFS -> PDF text -> Ollama
```

## Pinata

Pinata is **demo/prototype infrastructure only**. The intended architecture is provider-independent and can use user- or consortium-operated IPFS nodes. Pinata is not the conceptual central store.

## Main API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/challenge` | Create a wallet-signature challenge |
| POST | `/api/auth/verify` | Verify wallet signature and obtain session token |
| GET | `/api/auth/me` | Return authenticated wallet |
| POST | `/api/records/upload` | Upload PDF; no patient identifier is accepted |
| POST | `/api/search/query` | RAG query |
| GET | `/api/verify/{record_hash}` | Verify on-chain record reference |

## Wallet contract migration

The bundled 40-record demo set was created before the wallet contract revision. The PDFs, CIDs and Chroma vectors remain valid; they do not need to be uploaded again.

After deploying the current contract:

```powershell
python blockchain/scripts/deploy.py
python scripts/migrate_seed_manifest.py
```

The deployer wallet is automatically an authorized clinician. To authorize a different clinician wallet:

```powershell
python scripts/authorize_wallet.py 0xYOUR_WALLET_ADDRESS
```

## Run backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```
