# Runtime Data (local only)

This folder holds local development data. Contents are gitignored except `.gitkeep` markers.

| Subfolder | Purpose |
|-----------|---------|
| `uploads/` | Off-chain medical record files (PDF, text, etc.) |
| `chromadb/` | ChromaDB vector store for RAG embeddings |

SQLite database file (`medical_records.db`) is created at project root or under `data/` per backend config.
