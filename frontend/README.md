# MedChain RAG Frontend

A lightweight React/Vite UI for the wallet-authenticated medical-record RAG backend.

## Included views

- **Wallet authentication** — MetaMask challenge/signature flow, then backend JWT session.
- **Dashboard** — clinician identity, architecture summary and quick actions.
- **Semantic Search** — calls `POST /api/search/query` and renders the generated answer plus record-hash/IPFS provenance cards.
- **Upload Record** — uploads a PDF to `POST /api/records/upload` and displays hash, CID, transaction hash and indexing status.
- **Verify Record** — calls `GET /api/verify/{record_hash}`.
- **Blockchain Explorer** — renders recent Hyperledger Besu blocks as connected visual blocks and shows block/transaction metadata.

There is intentionally no patient-management CRUD. Clinician identity is the authenticated wallet and records are referenced by cryptographic content identity.

## Run

From `F:\rag_blockchain_medical_records\frontend`:

```powershell
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

The Vite dev server proxies `/api/*` to:

```text
http://127.0.0.1:8000
```

So FastAPI should be running before you use Search, Upload, Verify or authentication.

## Environment

Copy `.env.example` to `.env` if you want to override defaults:

```powershell
Copy-Item .env.example .env
```

Defaults:

```env
VITE_API_BASE_URL=
VITE_BESU_RPC_URL=/besu-rpc
VITE_CHAIN_ID=1337
```

`VITE_API_BASE_URL` is intentionally blank in development so requests use the Vite proxy and avoid browser CORS issues with FastAPI.

## MetaMask authentication

The browser flow is:

```text
MetaMask account
   ↓
POST /api/auth/challenge
   ↓
personal_sign
   ↓
POST /api/auth/verify
   ↓
JWT session
```

The private key is never sent to this frontend or backend. MetaMask performs the signature locally.

The wallet must already be authorized as a clinician by the smart contract.

## Blockchain page and CORS

The Blockchain page reads `eth_blockNumber`, `eth_chainId` and `eth_getBlockByNumber` from Besu. In development the Vite server proxies `/besu-rpc` to `http://127.0.0.1:8545`, so the browser does not need direct CORS access to Besu.

For deployment, replace that development proxy with a small authenticated FastAPI blockchain-read endpoint or a tightly restricted reverse proxy.

Do **not** expose unrestricted Besu JSON-RPC publicly in production.

## Pinata / IPFS architecture note

The UI labels provenance as IPFS-based. Pinata is only the current prototype pinning/gateway provider; it is not the conceptual storage architecture. A consortium deployment can replace it with provider-independent hospital/user-operated IPFS nodes while preserving CID-based retrieval.
