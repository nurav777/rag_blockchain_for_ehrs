# Database

The current architecture has no application relational database.

Identity is a verified Ethereum wallet address. Medical-record references are resolved from the Besu registry and record content is retrieved from IPFS. Chroma is only a semantic vector index and stores embeddings plus opaque record-hash/chunk metadata.
