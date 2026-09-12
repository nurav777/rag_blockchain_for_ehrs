# Backend (FastAPI)

Wallet-authenticated API for IPFS/Besu/Chroma medical-record retrieval.

There is no SQLAlchemy/SQLite identity layer. Clinician identity comes from an Ethereum-compatible wallet signature and on-chain clinician authorization.

## Main modules

```text
app/
├── main.py
├── config.py
├── dependencies/auth.py
├── routers/
│   ├── auth.py
│   ├── records.py
│   ├── search.py
│   └── verify.py
├── schemas/
│   ├── auth.py
│   ├── record.py
│   └── search.py
└── services/
    ├── auth_service.py
    ├── blockchain_service.py
    ├── pinata_service.py
    ├── rag_service.py
    └── record_service.py
```

Run:

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload
```
