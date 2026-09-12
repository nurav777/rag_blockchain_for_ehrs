# RAG

```text
clinician query
 -> query embedding
 -> Chroma top-k
 -> record_hash + chunk_index
 -> Besu record registry
 -> IPFS CID
 -> IPFS PDF
 -> deterministic chunk reconstruction
 -> Ollama answer
```

Chroma does not persist PDF plaintext or person identity metadata.
