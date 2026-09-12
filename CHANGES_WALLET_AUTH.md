# Wallet-only identity migration

## What changed

- Removed SQLite/SQLAlchemy completely.
- Removed doctor/password accounts.
- Removed patient models, routes, schemas and IDs.
- Added wallet challenge/signature authentication.
- Added on-chain clinician-wallet authorization.
- Record upload accepts only a PDF plus the wallet-derived session token.
- Smart contract record metadata is now `recordHash`, `ipfsCid`, `uploaderWallet`, `timestamp`.
- Future synthetic seed PDFs contain no person-name field and are deleted locally after upload.
- Existing 40 seeded CIDs/hashes are preserved in `data/demo_seed_manifest.json`.
- RAG redacts legacy `Patient:` name lines before LLM context/embedding.

## Required migration order

From the project root, with Besu running:

```powershell
pip install -r backend/requirements.txt
python blockchain/scripts/deploy.py
python scripts/migrate_seed_manifest.py
python scripts/reindex_seed_manifest.py
```

The first command installs the wallet-auth dependencies. Deployment writes the new contract address/ABI. Migration re-registers the 40 existing hash-to-CID references without re-uploading IPFS content. Reindexing rebuilds Chroma from those CIDs with legacy synthetic name lines redacted.

The deployer wallet is authorized automatically. For another wallet:

```powershell
python scripts/authorize_wallet.py 0xYOUR_WALLET_ADDRESS
```

Then start FastAPI:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```
