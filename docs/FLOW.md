# Flow

## Authentication

1. Client supplies wallet address.
2. Backend returns a short-lived challenge message.
3. Wallet signs the challenge.
4. Backend recovers the signer address.
5. Backend verifies that wallet is an authorized clinician on Besu.
6. Backend issues a short-lived session token whose subject is the wallet address.

## Upload

1. Authenticated wallet uploads PDF.
2. Backend calculates SHA-256 record hash.
3. PDF is pinned to IPFS through Pinata for the prototype.
4. Backend relays record registration to Besu with the verified uploader wallet.
5. Chroma stores embeddings plus `record_hash` and `chunk_index` only.

## Search

1. Authenticated wallet submits query.
2. Chroma returns relevant hash/chunk references.
3. Besu resolves hash to CID.
4. PDF is fetched from IPFS.
5. The relevant chunk is reconstructed and provided to Ollama.
