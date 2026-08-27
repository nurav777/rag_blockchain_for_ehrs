# Blockchain-Based Secure Medical Record Storage and Retrieval using RAG

Final Year Engineering project for a **three-hospital consortium** (Hospital A, Hospital B, Hospital C). Doctors upload medical records off-chain; the system uses **IPFS**, **blockchain metadata**, and **RAG** for secure storage, integrity verification, and semantic search.

> **Important:** Medical record content (PDFs) is **never stored on the blockchain**. Only metadata (hash, doctor ID, hospital ID, timestamp, IPFS CID) is registered on-chain.

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | FastAPI, SQLAlchemy, SQLite, Web3.py |
| **Blockchain** | Hyperledger Besu (QBFT), Solidity, Docker |
| **IPFS** | Pinata |
| **AI / RAG** | Sentence Transformers, ChromaDB, Ollama |
| **Frontend** | React, Vite, Tailwind CSS (scaffolded) |

---

## System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         Doctor (Browser / API Client)                   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS + JWT
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (backend/)                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │   Auth   │ │ Patients │ │ Records  │ │  Search  │ │   Verify     │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────────────┘  │
│       │            │            │            │                          │
│       ▼            ▼            ▼            ▼                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        Service Layer                             │   │
│  │  auth_service │ patient_service │ record_service │ rag_service    │   │
│  │  pinata_service │ blockchain_service                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└───────┬───────────────┬────────────────┬───────────────┬───────────────┘
        │               │                │               │
        ▼               ▼                ▼               ▼
   ┌─────────┐   ┌─────────────┐  ┌──────────┐  ┌─────────────────────┐
   │ SQLite  │   │ data/uploads│  │ ChromaDB │  │ Hyperledger Besu    │
   │ (metadata│   │ (PDF files) │  │(vectors) │  │ (3-node consortium)│
   └─────────┘   └──────┬──────┘  └──────────┘  └─────────────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │ Pinata IPFS │
                   └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │   Ollama    │
                   │  (LLM/RAG)  │
                   └─────────────┘
```

---

## Project Structure

```text
rag_blockchain_medical_records/
├── backend/              # FastAPI REST API
│   └── app/
│       ├── routers/      # HTTP endpoints
│       ├── services/     # Business logic
│       ├── models/       # SQLAlchemy ORM
│       └── schemas/      # Pydantic validation
├── blockchain/           # Besu network + Solidity contract
│   ├── besu/             # Genesis, node keys, static nodes
│   ├── contracts/        # MedicalRecordRegistry.sol
│   └── abi/              # Contract ABI
├── frontend/             # React UI (placeholder pages)
├── data/                 # Runtime data (DB, uploads, ChromaDB)
├── docs/                 # Design documentation
├── README.md             # This file — architecture & flows
└── TESTING.md            # Components, test cases, setup guide
```

---

## Upload Flow

When a doctor uploads a PDF medical record:

```text
Doctor Login (JWT)
       ↓
Validate PDF
       ↓
Generate SHA-256 Hash
       ↓
Store PDF locally (data/uploads/)
       ↓
Save metadata to SQLite
       ↓
Extract text + Generate embedding → Store in ChromaDB
       ↓
Upload PDF to Pinata IPFS → Save CID in SQLite
       ↓
Call registerRecord() on Besu → Save transaction hash in SQLite
       ↓
Return record metadata (+ warnings if IPFS/blockchain skipped)
```

### What is stored where

| Data | Location |
|------|----------|
| PDF file | Local disk + Pinata IPFS |
| Patient/diagnosis metadata | SQLite |
| Vector embeddings | ChromaDB |
| Record hash, CID, doctor/hospital IDs | Blockchain (metadata only) |

---

## Search / Retrieval Flow (RAG)

When a doctor submits a natural-language query:

```text
Doctor Query
       ↓
Generate query embedding (Sentence Transformers)
       ↓
Search ChromaDB → Top 5 similar records
       ↓
Verify record hashes on blockchain (getRecord)
       ↓
Download PDFs from Pinata (fallback: local file)
       ↓
Build context from verified record excerpts
       ↓
Send context + query to Ollama
       ↓
Return AI answer with citations
```

---

## Blockchain Consortium

Three Besu validator nodes represent the hospital consortium:

| Node | Hospital | RPC Port |
|------|----------|----------|
| hospital-a | Hospital A | 8545 |
| hospital-b | Hospital B | — |
| hospital-c | Hospital C | — |

- **Consensus:** QBFT
- **Chain ID:** 1337
- **Contract:** `MedicalRecordRegistry.sol`

### On-chain functions

| Function | Purpose |
|----------|---------|
| `registerRecord()` | Store record metadata hash |
| `verifyRecord()` | Compare a hash against on-chain data |
| `getRecord()` | Read stored metadata (used during RAG verification) |

---

## Database Schema (SQLite)

| Table | Key Fields |
|-------|------------|
| **doctors** | id, name, email, hashed_password |
| **patients** | id, name, age, gender, hospital_id |
| **medical_records** | id, patient_id, doctor_id, diagnosis, record_hash, file_path, ipfs_cid, tx_hash |

Hospital IDs: `hospital_a`, `hospital_b`, `hospital_c`

---

## API Overview

| Prefix | Purpose |
|--------|---------|
| `/api/auth` | Doctor login, JWT, profile |
| `/api/patients` | Patient CRUD |
| `/api/records` | PDF upload |
| `/api/search` | RAG semantic search |
| `/api/verify` | Reserved for future verification endpoints |

Interactive API docs: `http://127.0.0.1:8000/docs`

---

## Security Model

- **Authentication:** JWT bearer tokens for all protected routes
- **Integrity:** SHA-256 hashing + blockchain verification
- **Off-chain storage:** PDFs on local disk and IPFS, not on-chain
- **Audit trail:** Blockchain timestamps and transaction hashes

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [TESTING.md](TESTING.md) | Component breakdown, test cases, full setup guide |
| [docs/FLOW.md](docs/FLOW.md) | Upload and search flow diagrams |
| [docs/BLOCKCHAIN.md](docs/BLOCKCHAIN.md) | Blockchain design notes |
| [docs/RAG.md](docs/RAG.md) | RAG pipeline notes |
| [blockchain/README.md](blockchain/README.md) | Besu network setup |
