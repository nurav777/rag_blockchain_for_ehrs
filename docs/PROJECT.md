# Project architecture

Components:

- FastAPI API
- Ethereum-wallet challenge/signature authentication
- Hyperledger Besu QBFT consortium chain
- Solidity medical-record registry
- IPFS for content-addressed record retrieval
- Pinata as prototype-only pinning infrastructure
- ChromaDB for embeddings and opaque retrieval metadata
- SentenceTransformers for embeddings
- Ollama for local generation

The backend has no patient-management or password-account subsystem.
