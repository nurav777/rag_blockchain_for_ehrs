# Testing & Setup Guide

This document breaks the project into components, provides API test cases with expected outputs, and explains how to run the full system locally.

For architecture and data flows, see [README.md](README.md).

---

## Table of Contents

1. [Component Breakdown](#component-breakdown)
2. [Prerequisites](#prerequisites)
3. [How to Run the Entire Project](#how-to-run-the-entire-project)
4. [Test Cases by Component](#test-cases-by-component)
5. [End-to-End Workflow Test](#end-to-end-workflow-test)
6. [Troubleshooting](#troubleshooting)

---

## Component Breakdown

### 1. Authentication (`backend/app/services/auth_service.py`)

| Item | Detail |
|------|--------|
| **Purpose** | Doctor login, JWT generation, password hashing |
| **Endpoints** | `POST /api/auth/login`, `GET /api/auth/me` |
| **Storage** | SQLite `doctors` table |
| **Dependencies** | bcrypt, python-jose |

### 2. Patient Management (`backend/app/services/patient_service.py`)

| Item | Detail |
|------|--------|
| **Purpose** | CRUD for patients across three hospitals |
| **Endpoints** | `POST/GET/PUT/DELETE /api/patients` |
| **Storage** | SQLite `patients` table |
| **Hospital IDs** | `hospital_a`, `hospital_b`, `hospital_c` |

### 3. Medical Record Upload (`backend/app/services/record_service.py`)

| Item | Detail |
|------|--------|
| **Purpose** | PDF validation, hashing, local storage, orchestration |
| **Endpoint** | `POST /api/records/upload` |
| **Storage** | SQLite `medical_records`, `data/uploads/` |
| **Integrates** | Pinata, ChromaDB indexing, blockchain registration |

### 4. Pinata IPFS (`backend/app/services/pinata_service.py`)

| Item | Detail |
|------|--------|
| **Purpose** | Upload PDFs to IPFS, download via gateway |
| **Config** | `PINATA_API_KEY`, `PINATA_SECRET_API_KEY`, `PINATA_GATEWAY_URL` |
| **Used in** | Upload (store CID), RAG search (retrieve files) |

### 5. Blockchain (`backend/app/services/blockchain_service.py`)

| Item | Detail |
|------|--------|
| **Purpose** | Register and verify record metadata on Besu |
| **Contract** | `MedicalRecordRegistry.sol` |
| **Config** | `BESU_RPC_URL`, `CONTRACT_ADDRESS`, `DEPLOYER_PRIVATE_KEY` |
| **Network** | 3-node QBFT consortium (Docker) |

### 6. RAG / Search (`backend/app/services/rag_service.py`)

| Item | Detail |
|------|--------|
| **Purpose** | Semantic search, blockchain verify, Ollama summarization |
| **Endpoint** | `POST /api/search/query` |
| **Storage** | ChromaDB (`data/chromadb/`) |
| **Dependencies** | Sentence Transformers, Ollama, pypdf |

### 7. Blockchain Network (`blockchain/`)

| Item | Detail |
|------|--------|
| **Purpose** | Local Hyperledger Besu consortium |
| **Nodes** | hospital-a (RPC 8545), hospital-b, hospital-c |
| **Start** | `docker compose up -d` from `blockchain/` |

### 8. Frontend (`frontend/`)

| Item | Detail |
|------|--------|
| **Purpose** | Doctor UI (scaffolded — pages exist as placeholders) |
| **Status** | Not yet wired to backend API |

---

## Prerequisites

| Tool | Version / Notes |
|------|-----------------|
| Python | 3.11+ |
| Docker Desktop | For Besu network |
| Ollama | For RAG answers — [ollama.com](https://ollama.com) |
| Pinata account | For IPFS upload/download (optional for local-only testing) |
| Git | Optional |

---

## How to Run the Entire Project

### Step 1 — Clone and configure environment

```powershell
cd f:\rag_blockchain_medical_records
copy .env.example .env
```

Edit `.env` and set at minimum:

```env
SECRET_KEY=your-dev-secret-key
PINATA_API_KEY=your_pinata_key
PINATA_SECRET_API_KEY=your_pinata_secret
BESU_RPC_URL=http://127.0.0.1:8545
CONTRACT_ADDRESS=0x...          # after deployment
DEPLOYER_PRIVATE_KEY=0x...       # genesis-funded account
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3
```

### Step 2 — Start the Besu blockchain network

```powershell
cd blockchain
docker compose up -d
docker compose ps
```

Verify RPC:

```powershell
curl.exe -X POST http://127.0.0.1:8545 -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_chainId\",\"params\":[],\"id\":1}"
```

**Expected:** `"result":"0x539"` (chain ID 1337)

> Deploy `MedicalRecordRegistry.sol` to Besu and set `CONTRACT_ADDRESS` in `.env`. The deploy script placeholder is at `blockchain/scripts/deploy.py`.

### Step 3 — Start Ollama

```powershell
ollama pull llama3
ollama serve
```

Verify: open `http://127.0.0.1:11434` or run `ollama list`.

### Step 4 — Install and run the backend

```powershell
cd f:\rag_blockchain_medical_records\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API available at: **http://127.0.0.1:8000**  
Swagger UI: **http://127.0.0.1:8000/docs**

### Step 5 — Seed a test doctor (first run only)

If no doctor exists in the database, create one via Python:

```powershell
cd backend
python -c "
from app.database import init_db, SessionLocal
from app.models.doctor import Doctor
from app.services.auth_service import hash_password

init_db()
db = SessionLocal()
if not db.query(Doctor).filter(Doctor.email == 'doctor@hospital-a.com').first():
    db.add(Doctor(name='Dr. Smith', email='doctor@hospital-a.com', hashed_password=hash_password('password123')))
    db.commit()
db.close()
print('Test doctor ready')
"
```

**Test credentials:** `doctor@hospital-a.com` / `password123`

### Step 6 — (Optional) Start frontend

The frontend is scaffolded but not fully implemented. When ready:

```powershell
cd frontend
npm install
npm run dev
```

---

## Test Cases by Component

Use **Swagger UI** (`/docs`) or **PowerShell** below. Replace `$token` after login.

---

### Component 1: Health Check

| | |
|---|---|
| **Endpoint** | `GET /health` |
| **Auth** | None |

**Input:** None

**Expected output (200):**
```json
{ "status": "ok" }
```

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

---

### Component 2: Authentication

#### TC-AUTH-01: Login success

| | |
|---|---|
| **Endpoint** | `POST /api/auth/login` |
| **Auth** | None |

**Input:**
```json
{
  "email": "doctor@hospital-a.com",
  "password": "password123"
}
```

**Expected output (200):**
```json
{
  "access_token": "<jwt_string>",
  "token_type": "bearer"
}
```

```powershell
$login = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/login" `
  -Method POST -ContentType "application/json" `
  -Body '{"email":"doctor@hospital-a.com","password":"password123"}'
$token = $login.access_token
```

#### TC-AUTH-02: Login failure

**Input:**
```json
{ "email": "doctor@hospital-a.com", "password": "wrongpassword" }
```

**Expected output (401):**
```json
{ "detail": "Incorrect email or password" }
```

#### TC-AUTH-03: Get current doctor

| | |
|---|---|
| **Endpoint** | `GET /api/auth/me` |
| **Auth** | Bearer token |

**Expected output (200):**
```json
{
  "id": 1,
  "name": "Dr. Smith",
  "email": "doctor@hospital-a.com"
}
```

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/me" `
  -Headers @{ Authorization = "Bearer $token" }
```

#### TC-AUTH-04: Unauthorized access

**Input:** No `Authorization` header

**Expected output (401):**
```json
{ "detail": "Not authenticated" }
```

---

### Component 3: Patient Management

#### TC-PAT-01: Create patient

| | |
|---|---|
| **Endpoint** | `POST /api/patients` |
| **Auth** | Bearer token |

**Input:**
```json
{
  "name": "John Doe",
  "age": 45,
  "gender": "male",
  "hospital_id": "hospital_a"
}
```

**Expected output (201):**
```json
{
  "id": 1,
  "name": "John Doe",
  "age": 45,
  "gender": "male",
  "hospital_id": "hospital_a"
}
```

#### TC-PAT-02: List patients

| | |
|---|---|
| **Endpoint** | `GET /api/patients` |

**Expected output (200):** Array of patient objects

#### TC-PAT-03: Filter by hospital

| | |
|---|---|
| **Endpoint** | `GET /api/patients?hospital_id=hospital_a` |

**Expected output (200):** Only patients with `hospital_id: "hospital_a"`

#### TC-PAT-04: Update patient

| | |
|---|---|
| **Endpoint** | `PUT /api/patients/1` |

**Input:**
```json
{ "age": 46 }
```

**Expected output (200):** Patient object with `"age": 46`

#### TC-PAT-05: Invalid hospital ID

**Input:**
```json
{ "name": "Jane", "age": 30, "gender": "female", "hospital_id": "hospital_x" }
```

**Expected output (422):** Validation error

---

### Component 4: Medical Record Upload

#### TC-REC-01: Upload PDF

| | |
|---|---|
| **Endpoint** | `POST /api/records/upload` |
| **Auth** | Bearer token |
| **Content-Type** | `multipart/form-data` |

**Input:**

| Field | Value |
|-------|-------|
| `patient_id` | `1` |
| `diagnosis` | `Hypertension` |
| `file` | Valid PDF file |

**Expected output (201):**
```json
{
  "id": 1,
  "patient_id": 1,
  "doctor_id": 1,
  "diagnosis": "Hypertension",
  "record_hash": "<64-char sha256 hex>",
  "file_path": "data/uploads/<uuid>.pdf",
  "ipfs_cid": "Qm...",
  "tx_hash": "0x...",
  "ipfs_warning": null,
  "blockchain_warning": null
}
```

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/records/upload" `
  -H "Authorization: Bearer $token" `
  -F "patient_id=1" `
  -F "diagnosis=Hypertension" `
  -F "file=@f:\rag_blockchain_medical_records\data\uploads\test-report.pdf"
```

#### TC-REC-02: Invalid file type

**Input:** Non-PDF file (e.g. `.txt`)

**Expected output (400):**
```json
{ "detail": "Only PDF files are allowed" }
```

#### TC-REC-03: Patient not found

**Input:** `patient_id=99999`

**Expected output (404):**
```json
{ "detail": "Patient not found" }
```

#### TC-REC-04: Pinata not configured

**Input:** Valid PDF, Pinata keys empty in `.env`

**Expected output (201):** Record saved; `ipfs_cid: null`, `ipfs_warning` contains `"Pinata credentials"`

---

### Component 5: RAG Search

#### TC-RAG-01: Semantic search

| | |
|---|---|
| **Endpoint** | `POST /api/search/query` |
| **Auth** | Bearer token |

**Prerequisites:** At least one record uploaded and indexed; Ollama running

**Input:**
```json
{
  "query": "What is the patient's diagnosis for hypertension?"
}
```

**Expected output (200):**
```json
{
  "query": "What is the patient's diagnosis for hypertension?",
  "answer": "<AI-generated summary based on verified records>",
  "citations": [
    {
      "record_id": 1,
      "patient_id": 1,
      "diagnosis": "Hypertension",
      "record_hash": "<sha256>",
      "ipfs_cid": "Qm...",
      "blockchain_verified": true,
      "score": 0.85,
      "excerpt": "Patient has elevated blood pressure...",
      "source": "pinata"
    }
  ]
}
```

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/search/query" `
  -Method POST `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body '{"query":"Summarize hypertension records for this patient"}'
```

#### TC-RAG-02: Empty query

**Input:**
```json
{ "query": "" }
```

**Expected output (422):** Validation error

#### TC-RAG-03: No indexed records

**Input:** Valid query, empty ChromaDB

**Expected output (200):**
```json
{
  "query": "...",
  "answer": "No relevant medical records were found.",
  "citations": []
}
```

#### TC-RAG-04: Ollama unavailable

**Input:** Valid query, Ollama not running

**Expected output (400):**
```json
{ "detail": "Ollama request failed: ..." }
```

---

### Component 6: Blockchain Network

#### TC-BC-01: Chain ID check

**Input:**
```json
{ "jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1 }
```

**Expected output:**
```json
{ "jsonrpc": "2.0", "id": 1, "result": "0x539" }
```

#### TC-BC-02: Node status

```powershell
cd blockchain
docker compose ps
```

**Expected:** All three containers (`besu-hospital-a`, `besu-hospital-b`, `besu-hospital-c`) running

---

## End-to-End Workflow Test

Run these steps in order to validate the full system:

```text
1. Start Besu          → docker compose up -d
2. Start Ollama        → ollama serve
3. Start backend       → uvicorn app.main:app --reload
4. Login               → POST /api/auth/login
5. Create patient      → POST /api/patients
6. Upload PDF record   → POST /api/records/upload
7. Search records      → POST /api/search/query
8. Verify in Swagger   → Check citations + blockchain_verified: true
```

### Expected end-state after step 6

| System | State |
|--------|-------|
| SQLite | Row in `medical_records` with hash, CID, tx_hash |
| Local disk | PDF in `data/uploads/` |
| ChromaDB | Embedding indexed for record ID |
| Pinata | PDF pinned with CID |
| Besu | `registerRecord` transaction mined |

### Expected end-state after step 7

| Field | Expected |
|-------|----------|
| `answer` | Non-empty AI summary |
| `citations[].blockchain_verified` | `true` (if Besu configured) |
| `citations[].source` | `"pinata"` or `"local"` |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: app` | Run uvicorn from `backend/` directory |
| PowerShell `curl` fails | Use `curl.exe` or `Invoke-RestMethod` |
| Swagger Authorize fails | Login via `POST /api/auth/login`, copy token, use PowerShell with `Bearer $token` |
| `401 Unauthorized` | Re-login; check token in `Authorization` header |
| Pinata upload skipped | Set `PINATA_API_KEY` and `PINATA_SECRET_API_KEY` in `.env` |
| Blockchain registration skipped | Start Besu, deploy contract, set `CONTRACT_ADDRESS` |
| Search returns no results | Upload a record first; ensure ChromaDB path is writable |
| Ollama timeout | Increase `OLLAMA_TIMEOUT` in `.env`; confirm `ollama pull llama3` |
| Docker Besu won't start | Ensure Docker Desktop is running |
| PDF upload 400 | File must start with `%PDF` magic bytes |

---

## Quick Reference — All Endpoints

| Method | Endpoint | Auth | Status |
|--------|----------|------|--------|
| GET | `/health` | No | Implemented |
| POST | `/api/auth/login` | No | Implemented |
| GET | `/api/auth/me` | Yes | Implemented |
| POST | `/api/patients` | Yes | Implemented |
| GET | `/api/patients` | Yes | Implemented |
| GET | `/api/patients/{id}` | Yes | Implemented |
| PUT | `/api/patients/{id}` | Yes | Implemented |
| DELETE | `/api/patients/{id}` | Yes | Implemented |
| POST | `/api/records/upload` | Yes | Implemented |
| POST | `/api/search/query` | Yes | Implemented |
| `/api/verify/*` | — | — | Not implemented |

---

## Related Documentation

- [README.md](README.md) — Architecture and flows
- [blockchain/README.md](blockchain/README.md) — Besu network details
- [docs/DATABASE.md](docs/DATABASE.md) — Database schema
- [docs/RAG.md](docs/RAG.md) — RAG pipeline design
