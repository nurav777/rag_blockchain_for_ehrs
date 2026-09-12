# Data directory

- `chromadb/` contains the local semantic vector index.
- `demo_seed_manifest.json` contains demo bookkeeping for record hashes, CIDs and transaction references.

The backend does not retain plaintext medical PDFs locally. The demo seeder creates a temporary PDF for upload and deletes it immediately afterward.

There is no relational application database in the current architecture.
