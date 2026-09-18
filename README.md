# Decentralized RAG for Blockchain-Based Medical Records

A decentralized medical-record retrieval system combining **IPFS, blockchain, semantic search, Retrieval-Augmented Generation (RAG), and wallet-based authentication**.

The project demonstrates how medical documents can be stored outside a conventional centralized database while retaining verifiable provenance and enabling natural-language retrieval. Medical records are stored through IPFS, their references and integrity information are registered on a private blockchain, and a vector index enables clinicians to search across records using semantic queries.

The application consists of a **FastAPI backend, Hyperledger Besu private blockchain, IPFS storage, ChromaDB vector index, local language model, wallet-based clinician authentication, and React frontend**.

---

## Overview

Traditional medical-record systems commonly rely on centralized databases controlled by a single organization. This project demonstrates an alternative architecture where storage, verification, retrieval, identity, and answer generation are handled by separate components.

The system separates these responsibilities as follows:

- **IPFS** stores and retrieves medical documents using content-addressed identifiers.
- **Hyperledger Besu** maintains an immutable registry connecting record hashes to IPFS CIDs and blockchain metadata.
- **ChromaDB** stores vector embeddings used for semantic discovery.
- **RAG** retrieves relevant records and provides their contents as context to a language model.
- **Ollama** runs the language model locally for answer generation.
- **Wallet authentication** establishes clinician identity without conventional username/password accounts.
- **FastAPI** coordinates authentication, storage, retrieval, verification, and RAG operations.
- **React** provides the user-facing interface.

This allows clinicians to search medical records using natural language while retaining the ability to trace retrieved information back to its IPFS record and blockchain registration.

---

## System Architecture

```text
                         Clinician
                             |
                             v
                     React Frontend
                             |
                  Wallet Authentication
                             |
                             v
                       FastAPI API
                             |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
       ChromaDB        Hyperledger Besu       IPFS
     Vector Index      Private Blockchain   Record Storage
          |                  |                  |
          |            Record Hash -> CID       |
          |                  |                  |
          +------------------+------------------+
                             |
                             v
                       RAG Retrieval
                             |
                             v
                     Local LLM / Ollama
                             |
                             v
                  Grounded Answer + Sources
```

The blockchain, IPFS layer, and vector database perform different functions and are intentionally kept separate.

---

## Clinician Authentication

Clinicians authenticate using an Ethereum-compatible wallet rather than an email address and password.

Authentication uses a signed challenge:

```text
Connect Wallet
      |
      v
Request Challenge
      |
      v
Backend Generates Challenge
      |
      v
Wallet Signs Challenge
      |
      v
Backend Recovers Signer
      |
      v
Verify Authorized Clinician
      |
      v
Issue Access Token
```

The clinician's private key remains under the control of the wallet and is never sent to the backend.

The frontend supports **MetaMask** for wallet interaction. For local development, an authorized test clinician wallet can be imported into MetaMask and used through the same authentication process.

---

## Medical Record Upload Flow

An authenticated clinician can upload a medical PDF through the frontend.

The record then passes through the storage, blockchain, and indexing pipeline.

```text
Medical PDF
    |
    v
Authenticated FastAPI Endpoint
    |
    +--------------------+
    |                    |
    v                    v
Calculate Record Hash   Upload to IPFS
                             |
                             v
                           CID
    |                        |
    +------------+-----------+
                 |
                 v
        Register on Blockchain
                 |
                 v
        Record Hash -> IPFS CID
                 |
                 v
          Extract Record Text
                 |
                 v
         Generate Embeddings
                 |
                 v
             ChromaDB
```

The medical PDF itself is not stored on the blockchain.

Instead, the blockchain maintains the information required to identify, locate, and verify the corresponding decentralized record.

---

## Search and RAG Flow

Clinicians can query the collection using natural language.

For example:

```text
Which medical records mention diabetes, and what treatments or medications are described?
```

The query passes through the following pipeline:

```text
Natural-Language Query
          |
          v
     Embedding Model
          |
          v
       ChromaDB
          |
          v
Relevant Record Hashes
          |
          v
  Blockchain Registry
          |
          v
       IPFS CIDs
          |
          v
 Retrieve Documents
          |
          v
 Verify Record Integrity
          |
          v
Relevant Record Content
          |
          v
      Local LLM
          |
          v
Answer + Provenance Information
```

### Semantic Discovery

The query is converted into an embedding and compared against the vectors stored in ChromaDB.

ChromaDB returns the most semantically relevant record hashes.

### Blockchain Resolution

The retrieved record hashes are resolved through the blockchain registry.

Each registered record provides information such as its:

- IPFS CID
- uploader wallet
- registration timestamp
- blockchain provenance

### IPFS Retrieval

The CID obtained from the blockchain is used to retrieve the corresponding medical document from IPFS.

The retrieved record can then be checked against its registered hash to verify its integrity.

### RAG Generation

Relevant record contents are supplied to the local language model together with the clinician's query.

The model generates an answer using the retrieved medical-record evidence rather than answering without context.

The API also returns citations containing provenance information for the retrieved records.

---

## Blockchain Layer

The project uses **Hyperledger Besu** to operate a private Ethereum-compatible blockchain.

A Solidity smart contract acts as the medical-record registry.

A registered record contains information such as:

```text
Record Hash
    |
    +---- IPFS CID
    |
    +---- Uploader Wallet
    |
    +---- Timestamp
    |
    +---- Blockchain Transaction
```

This provides an immutable relationship between a medical record and its decentralized storage reference.

When the RAG system retrieves a record, the blockchain can be consulted to confirm where the record is stored and whether the retrieved document corresponds to the registered record.

### Blockchain Visualization

The frontend also contains a blockchain explorer-style interface.

Recent Besu blocks are displayed as connected blocks:

```text
+---------------+      +---------------+      +---------------+
|   Block #103  | ---> |   Block #102  | ---> |   Block #101  |
|               |      |               |      |               |
| Hash          |      | Hash          |      | Hash          |
| Parent Hash   |      | Parent Hash   |      | Parent Hash   |
| Transactions  |      | Transactions  |      | Transactions  |
| Timestamp     |      | Timestamp     |      | Timestamp     |
+---------------+      +---------------+      +---------------+
```

Individual blocks can be inspected to view their metadata and transactions.

The visualization obtains block information from the local Besu JSON-RPC interface.

---

## IPFS Storage

Medical PDFs are stored using **IPFS content addressing**.

A conventional application might identify a document using a server-specific path:

```text
/server/records/report.pdf
```

IPFS instead identifies the document by its content:

```text
Qm...
```

This value is the document's **Content Identifier (CID)**.

The blockchain stores the CID associated with a registered record, allowing the application to locate the document without storing the document itself on-chain.

### Pinata in the Current Prototype

The current implementation uses **Pinata as an IPFS pinning provider** for development and demonstration.

Pinata simplifies uploading and maintaining the availability of files during the prototype.

It is not a fundamental dependency of the architecture.

A larger deployment could instead use independently operated IPFS nodes, including nodes maintained by participating hospitals or healthcare organizations.

The architecture remains:

```text
Record Hash
     |
     v
Blockchain
     |
     v
IPFS CID
     |
     v
IPFS Network
     |
     v
Medical Record
```

The RAG and blockchain layers therefore depend on IPFS content identifiers rather than on a particular IPFS provider.

---

## Vector Search

The project uses **ChromaDB** as its vector index.

Medical-record text is converted into embeddings and indexed so that semantically related records can be discovered from natural-language queries.

The vector database is used for **discovery rather than authoritative document storage**.

Its primary role is:

```text
Query
  |
  v
Embedding
  |
  v
Similarity Search
  |
  v
Record Hash
```

The record hash connects the semantic retrieval layer back to the blockchain.

The blockchain then provides the IPFS CID required to retrieve the actual record.

This separation prevents the vector database from becoming the authoritative source for the medical document.

---

## Local Language Model

Answer generation is performed using a locally hosted language model through **Ollama**.

The model receives:

```text
Clinician Query
       +
Retrieved Medical Record Evidence
       |
       v
   Local LLM
       |
       v
Grounded Answer
```

The language model is responsible for synthesizing an answer from the retrieved evidence.

It is not treated as the authoritative source of the underlying medical-record information.

---

## Record Verification

The system maintains a cryptographic hash for each registered record.

When a document is retrieved, its content can be hashed again and compared against the value registered on the blockchain.

Conceptually:

```text
Retrieved PDF
     |
     v
Calculate Hash
     |
     +----------------------+
     |                      |
     v                      v
Retrieved Hash       Blockchain Hash
     |                      |
     +----------+-----------+
                |
                v
             Compare
                |
        +-------+-------+
        |               |
        v               v
     Verified       Mismatch
```

This provides a mechanism for detecting whether the retrieved record differs from the content originally registered by the system.

---

## Wallet-Based Identity

Clinician identity is represented using blockchain wallet addresses.

The application does not require a traditional username/password authentication system.

```text
Wallet Address
      |
      v
Signed Challenge
      |
      v
Signature Verification
      |
      v
Authorized Clinician
```

MetaMask can perform the signing operation directly in the browser.

The frontend receives the public wallet address while the wallet retains control of the private key.

After successful verification, the backend issues an access token that can be used for protected API operations such as searching and uploading records.

---

## Frontend

The project includes a React and Vite frontend for interacting with the complete system.

The interface provides:

- Wallet connection
- MetaMask authentication
- Clinician dashboard
- Natural-language medical-record search
- RAG-generated answers
- Retrieved-record citations
- Blockchain verification status
- IPFS CID and record provenance
- PDF record upload
- Record verification
- Blockchain visualization
- Block and transaction inspection

The frontend communicates with the FastAPI backend for application operations and with the local Besu RPC interface for blockchain visualization.

---

## Backend

The backend is implemented using **FastAPI**.

It coordinates communication between the frontend and the different infrastructure components.

Its responsibilities include:

- wallet challenge generation
- wallet signature verification
- clinician authorization
- access-token management
- medical-record upload
- record hashing
- IPFS communication
- blockchain interaction
- document extraction
- vector indexing
- semantic retrieval
- RAG orchestration
- record verification
- citation generation

The backend therefore acts as the orchestration layer connecting the decentralized storage, blockchain, vector retrieval, and language-model components.

---

## Technology Stack

| Layer                   | Technology                           |
| ----------------------- | ------------------------------------ |
| Frontend                | React, Vite                          |
| Backend                 | Python, FastAPI                      |
| Authentication          | Ethereum Wallet Signatures, MetaMask |
| Blockchain              | Hyperledger Besu                     |
| Smart Contracts         | Solidity                             |
| Blockchain Interaction  | Web3.py                              |
| Decentralized Storage   | IPFS                                 |
| Prototype IPFS Provider | Pinata                               |
| Vector Database         | ChromaDB                             |
| Embeddings              | Sentence Transformers                |
| Local LLM Runtime       | Ollama                               |
| Document Format         | PDF                                  |

---

## Project Structure

```text
rag_blockchain_medical_records/
|
├── backend/
│   └── app/
│       ├── routers/
│       ├── schemas/
│       ├── services/
│       └── main.py
│
├── blockchain/
│   ├── contracts/
│   └── abi/
│
├── data/
│   ├── synthetic_records/
│   └── chromadb/
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── pages/
│       └── services/
│
├── scripts/
│
└── README.md
```

The project is separated into frontend, backend, blockchain, data, and supporting script layers so that each part of the architecture remains independently understandable.

---

## Synthetic Medical Records

The current dataset consists of synthetic medical PDFs created for development and evaluation.

The records contain example information such as:

- diagnoses
- medications
- vital signs
- clinical assessments
- recommendations
- follow-up instructions

These records allow the complete pipeline to be tested without depending on external medical datasets.

The synthetic collection is used to evaluate:

- IPFS storage
- blockchain registration
- record hashing
- semantic retrieval
- embedding quality
- RAG generation
- provenance tracking
- integrity verification

---

## Example Retrieval

A clinician can submit a query such as:

```text
Which medical records mention diabetes, and what treatments or medications are described?
```

ChromaDB identifies records that are semantically relevant to the query.

For each result, the application can resolve:

```text
Vector Search
     |
     v
Record Hash
     |
     v
Blockchain
     |
     v
IPFS CID
     |
     v
Medical PDF
```

The retrieved records are verified and supplied to the language model.

The final API response contains both the generated answer and citations.

A citation contains information such as:

```text
record_hash
ipfs_cid
chunk_index
blockchain_verified
relevance_score
excerpt
source
```

This allows the generated response to remain connected to the records from which its evidence was obtained.

---

## Why Combine Blockchain, IPFS, and RAG?

The technologies in the project solve different parts of the problem.

### IPFS

Provides content-addressed storage for medical documents.

### Blockchain

Provides an immutable registry connecting record hashes, IPFS CIDs, uploader wallets, and timestamps.

### ChromaDB

Provides efficient semantic discovery across medical-record content.

### RAG

Allows clinicians to ask natural-language questions and receive answers based on retrieved records.

### Wallet Authentication

Provides cryptographic clinician identity without maintaining conventional login credentials.

### Local LLM

Generates answers from retrieved evidence while keeping the language-model runtime within the local application environment.

Together, the architecture separates:

```text
Identity
   |
Storage
   |
Verification
   |
Discovery
   |
Retrieval
   |
Generation
```

rather than placing all of these responsibilities inside a single centralized database or application.

---

## Potential Applications

The architecture can be extended to systems involving:

- Cross-organization medical-record retrieval
- Healthcare consortium data sharing
- Tamper-evident medical-document registries
- Provenance-aware clinical information retrieval
- Decentralized health-record research
- Blockchain-verified document retrieval
- Auditable RAG systems
- Inter-hospital information exchange
- Distributed medical knowledge retrieval

The same architecture can also be adapted to other document systems where decentralized storage, provenance, semantic search, and verifiable retrieval are required.

---

## Current Prototype

The current implementation demonstrates the complete core pipeline:

```text
Wallet Authentication
        |
        v
Medical Record Upload
        |
        v
IPFS Storage
        |
        v
Blockchain Registration
        |
        v
Vector Indexing
        |
        v
Semantic Retrieval
        |
        v
Blockchain + IPFS Resolution
        |
        v
Record Verification
        |
        v
RAG Answer Generation
        |
        v
Verified Sources and Provenance
```

The system demonstrates how decentralized storage, blockchain verification, semantic retrieval, wallet-based identity, and locally generated RAG responses can operate together as a unified medical-record retrieval architecture.
