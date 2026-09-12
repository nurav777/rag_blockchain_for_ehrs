# Testing the wallet-only backend

## 1. Deploy the current registry

The current Solidity contract stores only `record_hash`, `ipfsCid`, `uploaderWallet` and `timestamp` for each record. The deployer wallet is authorized automatically.

```powershell
python blockchain/scripts/deploy.py
```

If you want to use a different wallet:

```powershell
python scripts/authorize_wallet.py 0xYOUR_WALLET_ADDRESS
```

## 2. Start FastAPI

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## 3. Wallet authentication

The client calls `/api/auth/challenge`, signs the returned `message` with its wallet using Ethereum personal-sign semantics, then submits the signature to `/api/auth/verify`.

For automated demo data, `scripts/seed_demo_records.py` performs this flow using `DEMO_WALLET_PRIVATE_KEY`; if that is empty it falls back to the local development deployer key.

No email/password account exists.

## 4. Preserve/migrate the existing 40 seeded records

After deploying the wallet contract:

```powershell
python scripts/migrate_seed_manifest.py
```

This re-registers the existing hash-to-CID references in the new contract. It does not upload the PDFs again and does not rebuild Chroma.

## 5. New synthetic records

```powershell
python scripts/seed_demo_records.py --count 3
```

Then, if successful:

```powershell
python scripts/seed_demo_records.py --count 40
```

Generated records contain no synthetic person name field. Upload requests contain only the PDF plus the wallet-derived Bearer session token.

## 6. Expected upload result

```json
{
  "record_hash": "...",
  "ipfs_cid": "...",
  "tx_hash": "0x...",
  "uploader_wallet": "0x...",
  "indexing_warning": null
}
```

## 7. Verify

```text
GET /api/verify/{record_hash}
Authorization: Bearer <wallet-session-token>
```

Expected fields include `verified`, `record_hash`, `ipfs_cid`, `uploader_wallet`, and `timestamp`.
